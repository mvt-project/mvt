# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import sqlite3
from typing import Optional

from mvt.common.module import DatabaseNotFoundError
from mvt.common.module_types import (
    ModuleAtomicResult,
    ModuleResults,
    ModuleSerializedResult,
)
from mvt.common.utils import convert_mactime_to_iso

from ..base import IOSExtraction

WHATSAPP_CONTACTS_BACKUP_IDS = [
    # SHA-1 of "AppDomainGroup-group.net.whatsapp.WhatsApp.shared-ContactsV2.sqlite"
    "b8548dc30aa1030df0ce18ef08b882cf7ab5212f",
]
WHATSAPP_CONTACTS_ROOT_PATHS = [
    "private/var/mobile/Containers/Shared/AppGroup/*/ContactsV2.sqlite",
]

# WhatsApp's standard disappearing-messages timer values, in seconds.
DISAPPEARING_DURATION_LABELS = {
    86400: "24 hours",
    604800: "7 days",
    1209600: "14 days",
    2592000: "30 days",
    7776000: "90 days",
}

# Output field -> candidate columns in ZWAADDRESSBOOKCONTACT, in order of
# preference. WhatsApp renames columns across versions, so the query is built
# from the columns actually present in the database.
COLUMN_CANDIDATES = {
    "whatsapp_id": ["ZWHATSAPPID"],
    "lid": ["ZLID"],
    "phone_number": ["ZPHONENUMBER"],
    "localized_phone_number": ["ZLOCALIZEDPHONENUMBER"],
    "full_name": ["ZFULLNAME"],
    "given_name": ["ZGIVENNAME"],
    "last_name": ["ZLASTNAME"],
    "user_name": ["ZUSERNAME"],
    "business_name": ["ZBUSINESSNAME"],
    "about_text": ["ZABOUTTEXT"],
    "about_emoji": ["ZABOUTEMOJI"],
    "notes": ["ZNOTES"],
    "disappearing_mode_duration": ["ZDISAPPEARINGMODEDURATION"],
    "disappearing_mode_timestamp": ["ZDISAPPEARINGMODETIMESTAMP"],
    "about_timestamp": ["ZABOUTTIMESTAMP"],
    "about_expiration_timestamp": ["ZABOUTEXPIRATIONTIMESTAMP"],
    "last_updated": ["ZLASTUPDATED"],
    "phone_status": ["ZPHONESTATUS", "ZPHONENUMBERSTATUS"],
    "sync_policy": ["ZSYNCPOLICY"],
}

STRING_FIELDS = [
    "whatsapp_id",
    "lid",
    "phone_number",
    "localized_phone_number",
    "full_name",
    "given_name",
    "last_name",
    "user_name",
    "business_name",
    "about_text",
    "about_emoji",
    "notes",
]

DATE_FIELDS = [
    "disappearing_mode_timestamp",
    "about_timestamp",
    "about_expiration_timestamp",
    "last_updated",
]


def _decode_string(value) -> Optional[str]:
    # CoreData stores string attributes as UTF-8 blobs in some WhatsApp
    # versions, so values can arrive as either bytes or str.
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return str(value)


def _label_duration(duration) -> str:
    if not duration:
        return "off"
    return DISAPPEARING_DURATION_LABELS.get(
        int(duration), f"{int(duration)} seconds"
    )


def _describe_contact(record: ModuleAtomicResult) -> str:
    contact = (
        record.get("whatsapp_id")
        or record.get("lid")
        or record.get("phone_number")
        or "unknown"
    )
    full_name = record.get("full_name")
    if full_name:
        contact = f"{contact} ({full_name})"
    return contact


class WhatsappContacts(IOSExtraction):
    """This module extracts WhatsApp contact records and per-contact
    disappearing-messages settings from ContactsV2.sqlite.

    ChatStorage.sqlite does not record the disappearing-messages state of 1:1
    chats: the authoritative timer is stored on each contact record in this
    database, alongside the mapping between a contact's LID and phone number
    identifiers.
    """

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

    def serialize(self, record: ModuleAtomicResult) -> ModuleSerializedResult:
        records = []
        contact = _describe_contact(record)

        if record.get("disappearing_mode_timestamp"):
            records.append(
                {
                    "timestamp": record["disappearing_mode_timestamp"],
                    "module": self.__class__.__name__,
                    "event": "disappearing_mode_set",
                    "data": (
                        f"WhatsApp disappearing messages timer set to "
                        f"'{record.get('disappearing_mode_label')}' "
                        f"for {contact}"
                    ),
                }
            )

        if record.get("about_timestamp"):
            data = f"WhatsApp about text of {contact} changed"
            about_text = record.get("about_text")
            if about_text:
                data += f' to "{about_text}"'
            records.append(
                {
                    "timestamp": record["about_timestamp"],
                    "module": self.__class__.__name__,
                    "event": "about_changed",
                    "data": data,
                }
            )

        if record.get("about_expiration_timestamp"):
            records.append(
                {
                    "timestamp": record["about_expiration_timestamp"],
                    "module": self.__class__.__name__,
                    "event": "about_expiration",
                    "data": (
                        f"WhatsApp about text of {contact} scheduled "
                        f"to expire"
                    ),
                }
            )

        if record.get("last_updated"):
            records.append(
                {
                    "timestamp": record["last_updated"],
                    "module": self.__class__.__name__,
                    "event": "contact_last_updated",
                    "data": f"WhatsApp contact record for {contact} updated",
                }
            )

        return records

    def run(self) -> None:
        try:
            self._find_ios_database(
                backup_ids=WHATSAPP_CONTACTS_BACKUP_IDS,
                root_paths=WHATSAPP_CONTACTS_ROOT_PATHS,
            )
        except DatabaseNotFoundError:
            self.log.warning(
                "Unable to find the WhatsApp ContactsV2.sqlite database in "
                "this backup or filesystem dump. WhatsApp disappearing "
                "messages settings and contact records cannot be extracted. "
                "This database is often missing from incremental backups."
            )
            return

        self.log.info(
            "Found WhatsApp contacts database at path: %s", self.file_path
        )

        assert self.file_path is not None
        conn = self._open_sqlite_db(self.file_path)
        cur = conn.cursor()
        try:
            try:
                cur.execute("PRAGMA table_info(ZWAADDRESSBOOKCONTACT)")
                available_columns = {row[1] for row in cur.fetchall()}
            except sqlite3.DatabaseError as exc:
                self.log.error(
                    "Unable to read the ZWAADDRESSBOOKCONTACT table schema: %s",
                    exc,
                )
                return

            if not available_columns:
                self.log.warning(
                    "The WhatsApp contacts database does not contain a "
                    "ZWAADDRESSBOOKCONTACT table"
                )
                return

            selected = {}
            for field, candidates in COLUMN_CANDIDATES.items():
                for candidate in candidates:
                    if candidate in available_columns:
                        selected[field] = candidate
                        break

            # A record with no duration column is "unknown", not "off": the
            # timer state cannot be determined from this database version.
            has_duration = "disappearing_mode_duration" in selected
            if not has_duration:
                self.log.warning(
                    "The ZDISAPPEARINGMODEDURATION column is not present in "
                    "this WhatsApp contacts database: disappearing messages "
                    "state is unknown"
                )

            columns = ["Z_PK"] + list(selected.values())
            cur.execute(
                f"SELECT {', '.join(columns)} FROM ZWAADDRESSBOOKCONTACT;"
            )
            fields = ["row_pk"] + list(selected.keys())

            for row in cur:
                record = dict(zip(fields, row))

                for field in STRING_FIELDS:
                    if field in record:
                        record[field] = _decode_string(record[field])
                    else:
                        record[field] = None

                for field in DATE_FIELDS:
                    if record.get(field) is not None:
                        record[field] = (
                            convert_mactime_to_iso(record[field]) or None
                        )
                    else:
                        record[field] = None

                duration = record.get("disappearing_mode_duration")
                if has_duration:
                    record["disappearing_mode_is_on"] = bool(duration)
                    record["disappearing_mode_label"] = _label_duration(
                        duration
                    )
                else:
                    record["disappearing_mode_duration"] = None
                    record["disappearing_mode_is_on"] = None
                    record["disappearing_mode_label"] = None

                record.setdefault("phone_status", None)
                record.setdefault("sync_policy", None)

                self.results.append(record)
        finally:
            cur.close()
            conn.close()

        total_ephemeral = sum(
            1 for record in self.results if record["disappearing_mode_is_on"]
        )
        self.log.info(
            "Extracted a total of %d WhatsApp contacts (%d with disappearing "
            "messages enabled)",
            len(self.results),
            total_ephemeral,
        )
