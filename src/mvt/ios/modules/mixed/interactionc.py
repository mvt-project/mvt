# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import datetime
import logging
import re
import sqlite3
from typing import Optional, Tuple

from mvt.common.module_types import (
    ModuleAtomicResult,
    ModuleResults,
    ModuleSerializedResult,
)
from mvt.common.utils import convert_mactime_to_iso

from ..base import IOSExtraction
from .whatsapp_contacts import WhatsappContacts

INTERACTIONC_BACKUP_IDS = [
    "1f5a521220a3ad80ebfdc196978df8e7a2e49dee",
]
INTERACTIONC_ROOT_PATHS = [
    "private/var/mobile/Library/CoreDuet/People/interactionC.db",
]

# The interaction record's creation date normally trails its start date by
# milliseconds: emitting it as a timeline event only duplicates the start
# date event. A large divergence, however, indicates the record was
# backfilled (sync, restore, or tampering) and is worth surfacing.
CREATION_DATE_DIVERGENCE_THRESHOLD = 3600.0

# Per-contact aggregate dates from ZCONTACTS are repeated on every
# interaction row of the same contact. They are serialized with a
# contact-centric data string so that timeline de-duplication collapses
# them into one event per contact.
CONTACT_EVENT_TEMPLATES = {
    "contacts_creation_date": "Contact {party} first recorded in interactionC",
    "first_incoming_sender_date": "First incoming interaction from {party}",
    "last_incoming_sender_date": "Last incoming interaction from {party}",
    "first_incoming_recipient_date": (
        "First incoming interaction where {party} was a recipient"
    ),
    "last_incoming_recipient_date": (
        "Last incoming interaction where {party} was a recipient"
    ),
    "first_outgoing_recipient_date": (
        "First outgoing interaction to {party}"
    ),
    "last_outgoing_recipient_date": (
        "Last outgoing interaction to {party}"
    ),
}


def _parse_iso(timestamp) -> Optional[datetime.datetime]:
    try:
        return datetime.datetime.strptime(
            timestamp, "%Y-%m-%d %H:%M:%S.%f"
        )
    except (TypeError, ValueError):
        return None


def _describe_delta(seconds: float) -> str:
    if seconds >= 86400:
        return f"{seconds / 86400:.0f} days"
    return f"{seconds / 3600:.0f} hours"
# Taken from APOLLO
# https://github.com/mac4n6/APOLLO/blob/master/modules/interaction_contact_interactions.txt
QUERIES = [
    """SELECT
            ZINTERACTIONS.ZSTARTDATE AS "start_date",
            ZINTERACTIONS.ZENDDATE AS "end_date",
            ZINTERACTIONS.ZBUNDLEID AS "bundle_id",
            ZINTERACTIONS.ZACCOUNT AS "account",
            ZINTERACTIONS.ZTARGETBUNDLEID AS "target_bundle_id",
            CASE ZINTERACTIONS.ZDIRECTION
                WHEN '0' THEN 'INCOMING'
                WHEN '1' THEN 'OUTGOING'
            END AS "direction",
            ZCONTACTS.ZDISPLAYNAME AS "sender_display_name",
            ZCONTACTS.ZIDENTIFIER AS "sender_identifier",
            ZCONTACTS.ZPERSONID AS "sender_personid",
            RECEIPIENTCONACT.ZDISPLAYNAME AS "recipient_display_name",
            RECEIPIENTCONACT.ZIDENTIFIER AS "recipient_identifier",
            RECEIPIENTCONACT.ZPERSONID AS "recipient_personid",
            ZINTERACTIONS.ZRECIPIENTCOUNT AS "recipient_count",
            ZINTERACTIONS.ZDOMAINIDENTIFIER AS "domain_identifier",
            ZINTERACTIONS.ZISRESPONSE AS "is_response",
            ZATTACHMENT.ZCONTENTTEXT AS "content",
            ZATTACHMENT.ZUTI AS "uti",
            ZATTACHMENT.ZCONTENTURL AS "attachment_content_url",
            ZATTACHMENT.ZSIZEINBYTES AS "size",
            ZATTACHMENT.ZPHOTOLOCALIDENTIFIER AS "photo_local_id",
            HEX(ZATTACHMENT.ZIDENTIFIER) AS "attachment_id",
            ZATTACHMENT.ZCLOUDIDENTIFIER AS "cloud_id",
            ZCONTACTS.ZINCOMINGRECIPIENTCOUNT AS "incoming_recipient_count",
            ZCONTACTS.ZINCOMINGSENDERCOUNT AS "incoming_sender_count",
            ZCONTACTS.ZOUTGOINGRECIPIENTCOUNT AS "outgoing_recipient_count",
            ZINTERACTIONS.ZCREATIONDATE AS "interactions_creation_date",
            ZCONTACTS.ZCREATIONDATE AS "contacts_creation_date",
            ZCONTACTS.ZFIRSTINCOMINGRECIPIENTDATE AS "first_incoming_recipient_date",
            ZCONTACTS.ZFIRSTINCOMINGSENDERDATE AS "first_incoming_sender_date",
            ZCONTACTS.ZFIRSTOUTGOINGRECIPIENTDATE AS "first_outgoing_recipient_date",
            ZCONTACTS.ZLASTINCOMINGSENDERDATE AS "last_incoming_sender_date",
            ZCONTACTS.ZLASTINCOMINGRECIPIENTDATE AS "last_incoming_recipient_date",
            ZCONTACTS.ZLASTOUTGOINGRECIPIENTDATE AS "last_outgoing_recipient_date",
            ZCONTACTS.ZCUSTOMIDENTIFIER AS "custom_id",
            ZINTERACTIONS.ZCONTENTURL AS "interaction_content_url",
            ZINTERACTIONS.ZLOCATIONUUID AS "location_uuid",
            ZINTERACTIONS.ZGROUPNAME AS "group_name",
            ZINTERACTIONS.ZDERIVEDINTENTIDENTIFIER AS "derivied_intent_id",
            ZINTERACTIONS.Z_PK AS "table_id"
    FROM ZINTERACTIONS
        LEFT JOIN ZCONTACTS
            ON ZINTERACTIONS.ZSENDER = ZCONTACTS.Z_PK
        LEFT JOIN Z_1INTERACTIONS
            ON ZINTERACTIONS.Z_PK == Z_1INTERACTIONS.Z_3INTERACTIONS
        LEFT JOIN ZATTACHMENT
            ON Z_1INTERACTIONS.Z_1ATTACHMENTS == ZATTACHMENT.Z_PK
        LEFT JOIN Z_2INTERACTIONRECIPIENT
            ON ZINTERACTIONS.Z_PK == Z_2INTERACTIONRECIPIENT.Z_3INTERACTIONRECIPIENT
        LEFT JOIN ZCONTACTS RECEIPIENTCONACT
            ON Z_2INTERACTIONRECIPIENT.Z_2RECIPIENTS == RECEIPIENTCONACT.Z_PK;
    """,
    """ SELECT
            ZINTERACTIONS.ZSTARTDATE AS "start_date",
            ZINTERACTIONS.ZENDDATE AS "end_date",
            ZINTERACTIONS.ZBUNDLEID AS "bundle_id",
            ZINTERACTIONS.ZACCOUNT AS "account",
            ZINTERACTIONS.ZTARGETBUNDLEID AS "target_bundle_id",
            CASE ZINTERACTIONS.ZDIRECTION
                WHEN '0' THEN 'INCOMING'
                WHEN '1' THEN 'OUTGOING'
            END AS "direction",
            ZCONTACTS.ZDISPLAYNAME AS "sender_display_name",
            ZCONTACTS.ZIDENTIFIER AS "sender_identifier",
            ZCONTACTS.ZPERSONID AS "sender_personid",
            RECEIPIENTCONACT.ZDISPLAYNAME AS "recipient_display_name",
            RECEIPIENTCONACT.ZIDENTIFIER AS "recipient_identifier",
            RECEIPIENTCONACT.ZPERSONID AS "recipient_personid",
            ZINTERACTIONS.ZRECIPIENTCOUNT AS "recipient_count",
            ZINTERACTIONS.ZDOMAINIDENTIFIER AS "domain_identifier",
            ZINTERACTIONS.ZISRESPONSE AS "is_response",
            ZATTACHMENT.ZCONTENTTEXT AS "content",
            ZATTACHMENT.ZUTI AS "uti",
            ZATTACHMENT.ZCONTENTURL AS "attachment_content_url",
            ZATTACHMENT.ZSIZEINBYTES AS "size",
            HEX(ZATTACHMENT.ZIDENTIFIER) AS "attachment_id",
            ZATTACHMENT.ZCLOUDIDENTIFIER AS "cloud_id",
            ZCONTACTS.ZINCOMINGRECIPIENTCOUNT AS "incoming_recipient_count",
            ZCONTACTS.ZINCOMINGSENDERCOUNT AS "incoming_sender_count",
            ZCONTACTS.ZOUTGOINGRECIPIENTCOUNT AS "outgoing_recipient_count",
            ZINTERACTIONS.ZCREATIONDATE AS "interactions_creation_date",
            ZCONTACTS.ZCREATIONDATE AS "contacts_creation_date",
            ZCONTACTS.ZFIRSTINCOMINGRECIPIENTDATE AS "first_incoming_recipient_date",
            ZCONTACTS.ZFIRSTINCOMINGSENDERDATE AS "first_incoming_sender_date",
            ZCONTACTS.ZFIRSTOUTGOINGRECIPIENTDATE AS "first_outgoing_recipient_date",
            ZCONTACTS.ZLASTINCOMINGSENDERDATE AS "last_incoming_sender_date",
            CASE ZCONTACTS.ZLASTINCOMINGRECIPIENTDATE
                WHEN '0' THEN '0'
                ELSE ZCONTACTS.ZLASTINCOMINGRECIPIENTDATE
         END AS "last_incoming_recipient_date",
         ZCONTACTS.ZLASTOUTGOINGRECIPIENTDATE AS "last_outgoing_recipient_date",
         ZCONTACTS.ZCUSTOMIDENTIFIER AS "custom_id",
         ZINTERACTIONS.ZCONTENTURL AS "interaction_content_url",
         ZINTERACTIONS.ZLOCATIONUUID AS "location_uuid",
         ZINTERACTIONS.Z_PK AS "table_id"
      FROM
         ZINTERACTIONS
         LEFT JOIN
            ZCONTACTS
            ON ZINTERACTIONS.ZSENDER = ZCONTACTS.Z_PK
         LEFT JOIN Z_1INTERACTIONS ON ZINTERACTIONS.Z_PK == Z_1INTERACTIONS.Z_3INTERACTIONS
         LEFT JOIN ZATTACHMENT ON Z_1INTERACTIONS.Z_1ATTACHMENTS == ZATTACHMENT.Z_PK
         LEFT JOIN Z_2INTERACTIONRECIPIENT ON ZINTERACTIONS.Z_PK== Z_2INTERACTIONRECIPIENT.Z_3INTERACTIONRECIPIENT
         LEFT JOIN ZCONTACTS RECEIPIENTCONACT ON Z_2INTERACTIONRECIPIENT.Z_2RECIPIENTS== RECEIPIENTCONACT.Z_PK
    """,
    """ SELECT
            ZINTERACTIONS.ZSTARTDATE AS "start_date",
            ZINTERACTIONS.ZENDDATE AS "end_date",
            ZINTERACTIONS.ZBUNDLEID AS "bundle_id",
            ZCONTACTS.ZDISPLAYNAME AS "sender_display_name",
            ZCONTACTS.ZIDENTIFIER AS "sender_identifier",
            ZCONTACTS.ZPERSONID AS "sender_personid",
            ZINTERACTIONS.ZDIRECTION AS "direction",
            ZINTERACTIONS.ZISRESPONSE AS "is_response",
            ZINTERACTIONS.ZMECHANISM AS "mechanism",
            ZINTERACTIONS.ZRECIPIENTCOUNT AS "recipient_count",
            ZINTERACTIONS.ZCREATIONDATE AS "interactions_creation_date",
            ZCONTACTS.ZCREATIONDATE AS "contacts_creation_date",
            ZCONTACTS.ZFIRSTINCOMINGRECIPIENTDATE AS "first_incoming_recipient_date",
            ZCONTACTS.ZFIRSTINCOMINGSENDERDATE AS "first_incoming_sender_date",
            ZCONTACTS.ZFIRSTOUTGOINGRECIPIENTDATE AS "first_outgoing_recipient_date",
            ZCONTACTS.ZLASTINCOMINGSENDERDATE AS "last_incoming_sender_date",
            CASE
                ZLASTINCOMINGRECIPIENTDATE
                WHEN
                    '0'
                THEN
                    '0'
                ELSE
                    ZCONTACTS.ZLASTINCOMINGRECIPIENTDATE
            END AS "last_incoming_recipient_date",
            ZCONTACTS.ZLASTOUTGOINGRECIPIENTDATE AS "last_outgoing_recipient_date",
            ZINTERACTIONS.ZACCOUNT AS 'account',
            ZINTERACTIONS.ZDOMAINIDENTIFIER AS "domain_identifier",
            ZCONTACTS.ZINCOMINGRECIPIENTCOUNT AS "incoming_recipient_count",
            ZCONTACTS.ZINCOMINGSENDERCOUNT AS "incoming_sender_count",
            ZCONTACTS.ZOUTGOINGRECIPIENTCOUNT AS "outgoing_recipient_count",
            ZCONTACTS.ZCUSTOMIDENTIFIER AS "custom_id",
            ZINTERACTIONS.ZCONTENTURL AS "interaction_content_url",
            ZINTERACTIONS.ZLOCATIONUUID AS "location_uuid",
            ZINTERACTIONS.Z_PK AS "table_id"
    FROM
        ZINTERACTIONS
        LEFT JOIN
            ZCONTACTS
        ON ZINTERACTIONS.ZSENDER = ZCONTACTS.Z_PK
    """,
    """ SELECT
            ZINTERACTIONS.ZSTARTDATE AS "start_date",
            ZINTERACTIONS.ZENDDATE AS "end_date",
            ZINTERACTIONS.ZCREATIONDATE AS "interactions_creation_date",
            ZINTERACTIONS.ZBUNDLEID AS "bundle_id",
            ZCONTACTS.ZDISPLAYNAME AS "sender_display_name",
            ZCONTACTS.ZIDENTIFIER AS "sender_identifier",
            ZCONTACTS.ZPERSONID AS "sender_personid",
            ZINTERACTIONS.ZDIRECTION AS "direction",
            ZINTERACTIONS.ZISRESPONSE AS "is_response",
            ZINTERACTIONS.ZMECHANISM AS "mechanism",
            ZCONTACTS.ZCREATIONDATE AS "contacts_creation_date",
            ZCONTACTS.ZFIRSTINCOMINGRECIPIENTDATE AS "first_incoming_recipient_date",
            ZCONTACTS.ZFIRSTINCOMINGSENDERDATE AS "first_incoming_sender_date",
            ZCONTACTS.ZFIRSTOUTGOINGRECIPIENTDATE AS "first_outgoing_recipient_date",
            ZCONTACTS.ZLASTINCOMINGSENDERDATE AS "last_incoming_sender_date",
            CASE
                ZLASTINCOMINGRECIPIENTDATE
                WHEN
                    '0'
                THEN
                    '0'
                ELSE
                    ZCONTACTS.ZLASTINCOMINGRECIPIENTDATE
            END AS "last_incoming_recipient_date",
            ZCONTACTS.ZLASTOUTGOINGRECIPIENTDATE AS "last_outgoing_recipient_date",
            ZINTERACTIONS.ZACCOUNT AS "account",
            ZINTERACTIONS.ZDOMAINIDENTIFIER AS "domain_identifier",
            ZCONTACTS.ZINCOMINGRECIPIENTCOUNT AS "incoming_recipient_count",
            ZCONTACTS.ZINCOMINGSENDERCOUNT AS "incoming_sender_count",
            ZCONTACTS.ZOUTGOINGRECIPIENTCOUNT AS "outgoing_recipient_count",
            ZINTERACTIONS.ZCONTENTURL AS "interaction_content_url",
            ZINTERACTIONS.ZLOCATIONUUID AS "location_uuid",
            ZINTERACTIONS.Z_PK AS "table_id"
    FROM
        ZINTERACTIONS
        LEFT JOIN
            ZCONTACTS
            ON ZINTERACTIONS.ZSENDER = ZCONTACTS.Z_PK
    """,
]


WHATSAPP_BUNDLE_ID = "net.whatsapp.WhatsApp"


class InteractionC(IOSExtraction):
    """This module extracts data from InteractionC db."""

    # WhatsApp identifies chat peers by LID in interactionC.db, which only the
    # WhatsApp contacts database can map back to a phone number and name.
    dependencies = [WhatsappContacts]

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        module_options: Optional[dict] = None,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[ModuleResults] = None,
    ) -> None:
        super().__init__(
            file_path=file_path,
            target_path=target_path,
            results_path=results_path,
            module_options=module_options,
            log=log,
            results=results,
        )

        self.timestamps = [
            "start_date",
            "end_date",
            "interactions_creation_date",
            "contacts_creation_date",
            "first_incoming_recipient_date",
            "first_incoming_sender_date",
            "first_outgoing_recipient_date",
            "last_incoming_sender_date",
            "last_incoming_recipient_date",
            "last_outgoing_recipient_date",
        ]

    @staticmethod
    def _describe_party(record: ModuleAtomicResult, prefix: str) -> Optional[str]:
        name = record.get(f"{prefix}_display_name") or record.get(
            f"{prefix}_resolved_name"
        )
        identifier = record.get(f"{prefix}_resolved_phone_number") or record.get(
            f"{prefix}_identifier"
        )
        if name and identifier:
            # A display name that is just a formatted copy of the phone
            # number adds no information.
            name_digits = re.sub(r"\D", "", name)
            if name_digits and name_digits == re.sub(r"\D", "", identifier):
                return identifier
            return f"{name} ({identifier})"
        return name or identifier or None

    def serialize(self, record: ModuleAtomicResult) -> ModuleSerializedResult:
        sender = self._describe_party(record, "sender")
        # The chat peer from the domain identifier stands in when the
        # recipient was not recorded (or the recipient join is unavailable).
        recipient = self._describe_party(record, "recipient") or self._describe_party(
            record, "domain"
        )
        direction = record.get("direction")
        if not sender and direction == "OUTGOING":
            sender = "local user"
        if not recipient and direction == "INCOMING":
            recipient = "local user"

        header = f"[{record['bundle_id']}]"
        if record.get("account"):
            header += f" {record['account']}"
        if direction:
            header += f" {direction}"

        data = f"{header} from {sender or 'unknown'} to {recipient or 'unknown'}"
        if record.get("group_name"):
            data += f" (group: {record['group_name']})"
        if record.get("content"):
            data += f": {record['content']}"

        records = []
        processed = []
        for timestamp in ("start_date", "end_date"):
            # Check if the record has the current timestamp.
            if timestamp not in record or not record[timestamp]:
                continue

            # Check if the timestamp was already processed.
            if record[timestamp] in processed:
                continue

            records.append(
                {
                    "timestamp": record[timestamp],
                    "module": self.__class__.__name__,
                    "event": timestamp,
                    "data": data,
                }
            )
            processed.append(record[timestamp])

        creation_event = self._serialize_creation_date(record, data)
        if creation_event:
            records.append(creation_event)

        # Contact-level aggregates describe the sender's contact record.
        party = self._describe_party(record, "sender")
        if party:
            for field, template in CONTACT_EVENT_TEMPLATES.items():
                if not record.get(field):
                    continue
                records.append(
                    {
                        "timestamp": record[field],
                        "module": self.__class__.__name__,
                        "event": field,
                        "data": template.format(party=party),
                    }
                )

        return records

    def _serialize_creation_date(
        self, record: ModuleAtomicResult, data: str
    ) -> Optional[dict]:
        """Serialize the interaction record's creation date only when it
        diverges from the start date enough to indicate the record was
        backfilled."""
        creation = record.get("interactions_creation_date")
        if not creation:
            return None

        event = {
            "timestamp": creation,
            "module": self.__class__.__name__,
            "event": "interactions_creation_date",
            "data": data,
        }

        start = _parse_iso(record.get("start_date"))
        creation_parsed = _parse_iso(creation)
        if not start or not creation_parsed:
            # Without a start date the creation date is the only anchor.
            return event

        delta = (creation_parsed - start).total_seconds()
        if abs(delta) < CREATION_DATE_DIVERGENCE_THRESHOLD:
            return None

        direction = "after" if delta > 0 else "before"
        event["data"] = (
            f"Interaction record created {_describe_delta(abs(delta))} "
            f"{direction} the event: {data}"
        )
        return event

    def _whatsapp_contact_maps(self) -> Tuple[dict, dict]:
        """Build LID and phone-digit lookup maps from the WhatsappContacts
        module results, when available."""
        by_lid: dict = {}
        by_phone: dict = {}
        contacts_module = self.dependency_modules.get(WhatsappContacts)
        if not contacts_module:
            return by_lid, by_phone

        for contact in contacts_module.results:
            name = contact.get("full_name") or contact.get("given_name")
            phone = contact.get("phone_number")
            entry = (phone, name)
            if contact.get("lid"):
                by_lid[contact["lid"]] = entry
            if phone:
                by_phone[re.sub(r"\D", "", phone)] = entry
            whatsapp_id = contact.get("whatsapp_id")
            if whatsapp_id and "@" in whatsapp_id:
                by_phone.setdefault(whatsapp_id.split("@")[0], entry)

        return by_lid, by_phone

    @staticmethod
    def _resolve_whatsapp_identifier(
        value, by_lid: dict, by_phone: dict
    ) -> Tuple[Optional[str], Optional[str]]:
        """Resolve a WhatsApp identifier (LID, JID or phone number) to a
        (phone_number, contact_name) tuple."""
        if not value:
            return None, None

        value = str(value)
        if value.endswith("@lid"):
            return by_lid.get(value, (None, None))
        if value.endswith("@g.us"):
            return None, None
        if value.endswith("@s.whatsapp.net"):
            digits = value.split("@")[0]
            phone, name = by_phone.get(digits, (None, None))
            return phone or f"+{digits}", name
        if value.startswith("+"):
            _, name = by_phone.get(re.sub(r"\D", "", value), (None, None))
            return None, name

        return None, None

    def _postprocess_results(self) -> None:
        by_lid, by_phone = self._whatsapp_contact_maps()

        for entry in self.results:
            # The fallback queries return ZDIRECTION raw instead of labelled.
            if entry.get("direction") in (0, "0"):
                entry["direction"] = "INCOMING"
            elif entry.get("direction") in (1, "1"):
                entry["direction"] = "OUTGOING"

            if entry.get("bundle_id") != WHATSAPP_BUNDLE_ID:
                continue

            candidates = {
                "sender": [entry.get("sender_identifier"), entry.get("custom_id")],
                "recipient": [entry.get("recipient_identifier")],
                "domain": [entry.get("domain_identifier")],
            }
            for prefix, values in candidates.items():
                phone = name = None
                for value in values:
                    phone, name = self._resolve_whatsapp_identifier(
                        value, by_lid, by_phone
                    )
                    if phone or name:
                        break
                entry[f"{prefix}_resolved_phone_number"] = phone
                entry[f"{prefix}_resolved_name"] = name

    def run(self) -> None:
        self._find_ios_database(
            backup_ids=INTERACTIONC_BACKUP_IDS, root_paths=INTERACTIONC_ROOT_PATHS
        )
        self.log.info("Found InteractionC database at path: %s", self.file_path)

        if not self.file_path:
            return
        conn = self._open_sqlite_db(self.file_path)
        cur = conn.cursor()

        try:
            try:
                cur.execute(QUERIES[0])
            except sqlite3.OperationalError:
                try:
                    cur.execute(QUERIES[1])
                except sqlite3.OperationalError:
                    try:
                        cur.execute(QUERIES[2])
                    except sqlite3.OperationalError:
                        try:
                            cur.execute(QUERIES[3])
                        except sqlite3.OperationalError as e:
                            self.log.info(
                                "Error while reading the InteractionC table: %s", e
                            )
                            return None

            names = [description[0] for description in cur.description]
            for item in cur:
                entry = {}
                for index, value in enumerate(item):
                    if names[index] in self.timestamps:
                        if value is None or isinstance(value, str):
                            entry[names[index]] = value
                        else:
                            entry[names[index]] = convert_mactime_to_iso(value)
                    else:
                        entry[names[index]] = value

                self.results.append(entry)
        finally:
            cur.close()
            conn.close()

        self._postprocess_results()

        self.log.info("Extracted a total of %d InteractionC events", len(self.results))
