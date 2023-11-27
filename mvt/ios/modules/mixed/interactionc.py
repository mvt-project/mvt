# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import sqlite3
from typing import Optional, Union

from mvt.common.utils import convert_mactime_to_iso

from ..base import IOSExtraction

INTERACTIONC_BACKUP_IDS = [
    "1f5a521220a3ad80ebfdc196978df8e7a2e49dee",
]
INTERACTIONC_ROOT_PATHS = [
    "private/var/mobile/Library/CoreDuet/People/interactionC.db",
]
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
            END 'DIRECTION' AS "direction",
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
            END 'DIRECTION' AS "direction",
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
         END 'LAST INCOMING RECIPIENT DATE' AS "last_incoming_recipient_date",
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


class InteractionC(IOSExtraction):
    """This module extracts data from InteractionC db."""

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        module_options: Optional[dict] = None,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[list] = None,
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

    def serialize(self, record: dict) -> Union[dict, list]:
        records = []
        processed = []
        for timestamp in self.timestamps:
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
                    "data": f"[{record['bundle_id']}] {record['account']} - "
                    f"from {record['sender_display_name']} ({record['sender_identifier']}) "
                    f"to {record.get('recipient_display_name', '')} ({record.get('recipient_identifier', '')}):"
                    f" {record.get('content', '')}",
                }
            )
            processed.append(record[timestamp])

        return records

    def run(self) -> None:
        self._find_ios_database(
            backup_ids=INTERACTIONC_BACKUP_IDS, root_paths=INTERACTIONC_ROOT_PATHS
        )
        self.log.info("Found InteractionC database at path: %s", self.file_path)

        conn = self._open_sqlite_db(self.file_path)
        cur = conn.cursor()

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

        cur.close()
        conn.close()

        self.log.info("Extracted a total of %d InteractionC events", len(self.results))
