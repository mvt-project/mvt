# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
import sqlite3
from typing import Dict, Optional

from mvt.common.module_types import (
    ModuleAtomicResult,
    ModuleResults,
    ModuleSerializedResult,
)
from mvt.common.utils import check_for_links, convert_mactime_to_iso

from ..base import IOSExtraction

WHATSAPP_BACKUP_IDS = [
    "7c7fba66680ef796b916b067077cc246adacf01d",
]
WHATSAPP_ROOT_PATHS = [
    "private/var/mobile/Containers/Shared/AppGroup/*/ChatStorage.sqlite",
]

WHATSAPP_LID_BACKUP_IDS = [
    # SHA-1 of "AppDomainGroup-group.net.whatsapp.WhatsApp.shared-LID.sqlite"
    "e794f6ffcc3c222535f47684a63d5178da3c4500",
]
WHATSAPP_LID_ROOT_PATHS = [
    "private/var/mobile/Containers/Shared/AppGroup/*/LID.sqlite",
]

# WhatsApp records the mapping between a contact's LID and phone number
# identifiers in the ZWAPHONENUMBERLIDPAIR table. Depending on the WhatsApp
# version this lives in a dedicated LID.sqlite database or in
# ChatStorage.sqlite itself.
LID_PAIRS_QUERY = """
    SELECT
        ZLID AS "lid",
        ZPHONENUMBER AS "phone_number",
        ZTIMESTAMP AS "pair_timestamp"
    FROM ZWAPHONENUMBERLIDPAIR;
"""

CHAT_SESSIONS_QUERY = """
    SELECT
        ZWACHATSESSION.Z_PK AS "session_pk",
        ZWACHATSESSION.ZCONTACTJID AS "contact_jid",
        ZWACHATSESSION.ZPARTNERNAME AS "partner_name",
        ZWACHATSESSION.ZSESSIONTYPE AS "session_type",
        ZWACHATSESSION.ZARCHIVED AS "archived",
        ZWACHATSESSION.ZREMOVED AS "removed",
        ZWACHATSESSION.ZMESSAGECOUNTER AS "message_counter",
        ZWACHATSESSION.ZLASTMESSAGEDATE AS "last_message_date",
        ZWAGROUPINFO.ZCREATIONDATE AS "group_creation_date",
        MIN(ZWAMESSAGE.ZMESSAGEDATE) AS "first_stored_message_date",
        MAX(ZWAMESSAGE.ZMESSAGEDATE) AS "last_stored_message_date",
        COUNT(ZWAMESSAGE.Z_PK) AS "stored_message_count"
    FROM ZWACHATSESSION
    LEFT JOIN ZWAGROUPINFO
        ON ZWACHATSESSION.ZGROUPINFO = ZWAGROUPINFO.Z_PK
    LEFT JOIN ZWAMESSAGE
        ON ZWAMESSAGE.ZCHATSESSION = ZWACHATSESSION.Z_PK
    GROUP BY ZWACHATSESSION.Z_PK;
"""

CHAT_SESSION_DATE_FIELDS = [
    "last_message_date",
    "group_creation_date",
    "first_stored_message_date",
    "last_stored_message_date",
]


def _describe_chat(record: ModuleAtomicResult) -> str:
    jid = record.get("contact_jid") or "unknown"
    name = record.get("partner_name")
    identifier = record.get("partner_resolved_phone_number") or jid
    label = f"'{name}' ({identifier})" if name else identifier
    is_group = jid.endswith("@g.us") or record.get("group_creation_date")
    if is_group:
        return f"WhatsApp group chat {label}"
    return f"WhatsApp chat with {label}"


class Whatsapp(IOSExtraction):
    """This module extracts all WhatsApp messages containing links, as well
    as per-chat records with the first and last interaction dates of each
    conversation."""

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
        if record.get("record_type") == "chat_session":
            return self._serialize_chat_session(record)
        if record.get("record_type") == "lid_phone_number_pair":
            if not record.get("pair_timestamp"):
                return []
            return {
                "timestamp": record["pair_timestamp"],
                "module": self.__class__.__name__,
                "event": "lid_pair_recorded",
                "data": (
                    f"WhatsApp associated LID {record.get('lid')} with "
                    f"phone number {record.get('phone_number')}"
                ),
            }

        text = record.get("ZTEXT", "").replace("\n", "\\n")
        links_text = ""
        if record.get("links"):
            links_text = " - Embedded links: " + ", ".join(record["links"])

        return {
            "timestamp": record.get("isodate"),
            "module": self.__class__.__name__,
            "event": "message",
            "data": f"'{text}' from {record.get('ZFROMJID', 'Unknown')}{links_text}",
        }

    def _serialize_chat_session(
        self, record: ModuleAtomicResult
    ) -> ModuleSerializedResult:
        records = []
        chat = _describe_chat(record)

        if record.get("group_creation_date"):
            records.append(
                {
                    "timestamp": record["group_creation_date"],
                    "module": self.__class__.__name__,
                    "event": "group_created",
                    "data": f"{chat} was created",
                }
            )

        if record.get("first_stored_message_date"):
            records.append(
                {
                    "timestamp": record["first_stored_message_date"],
                    "module": self.__class__.__name__,
                    "event": "chat_first_message",
                    "data": f"First stored message in {chat}",
                }
            )

        # The chat session's own last-message date is authoritative: it can
        # postdate the newest stored message if that message was deleted.
        last_message_date = record.get("last_message_date") or record.get(
            "last_stored_message_date"
        )
        if last_message_date:
            records.append(
                {
                    "timestamp": last_message_date,
                    "module": self.__class__.__name__,
                    "event": "chat_last_message",
                    "data": f"Last message in {chat}",
                }
            )

        return records

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        url_batches = [result.get("links", []) for result in self.results]
        for result, ioc_match in zip(
            self.results, self.indicators.check_url_batches(url_batches)
        ):
            if ioc_match:
                self.alertstore.critical(
                    ioc_match.message, "", result, matched_indicator=ioc_match.ioc
                )

    def collect_url_results(self) -> None:
        for message in self.results:
            for url in message.get("links", []):
                self.add_url_result(url, message.get("isodate"), "whatsapp")

    def run(self) -> None:
        self._find_ios_database(
            backup_ids=WHATSAPP_BACKUP_IDS, root_paths=WHATSAPP_ROOT_PATHS
        )
        self.log.info("Found WhatsApp database at path: %s", self.file_path)

        if not self.file_path:
            return
        conn = self._open_sqlite_db(self.file_path)
        cur = conn.cursor()

        # Query all messages and join tables which can contain media attachments
        # and links.
        cur.execute(
            """
            SELECT
                ZWAMESSAGE.*,
                ZWAMEDIAITEM.ZAUTHORNAME,
                ZWAMEDIAITEM.ZMEDIAURL,
                ZWAMESSAGEDATAITEM.ZCONTENT1,
                ZWAMESSAGEDATAITEM.ZCONTENT2,
                ZWAMESSAGEDATAITEM.ZMATCHEDTEXT,
                ZWAMESSAGEDATAITEM.ZSUMMARY,
                ZWAMESSAGEDATAITEM.ZTITLE
            FROM ZWAMESSAGE
            LEFT JOIN ZWAMEDIAITEM ON ZWAMEDIAITEM.ZMESSAGE = ZWAMESSAGE.Z_PK
            LEFT JOIN ZWAMESSAGEDATAITEM ON
                ZWAMESSAGEDATAITEM.ZMESSAGE = ZWAMESSAGE.Z_PK;
        """
        )
        names = [description[0] for description in cur.description]

        for message_row in cur:
            message = {}
            for index, value in enumerate(message_row):
                message[names[index]] = value

            message["isodate"] = convert_mactime_to_iso(
                message.get("ZMESSAGEDATE") or 0
            )
            message["ZTEXT"] = message["ZTEXT"] if message["ZTEXT"] else ""

            # Extract links from the WhatsApp message. URLs can be stored in
            # multiple fields/columns.
            # Check each of them!
            message_links = []
            fields_with_links = [
                "ZTEXT",
                "ZMATCHEDTEXT",
                "ZMEDIAURL",
                "ZCONTENT1",
                "ZCONTENT2",
            ]
            for field in fields_with_links:
                if message.get(field):
                    message_links.extend(check_for_links(message.get(field, "")))

            # Remove WhatsApp internal media URLs.
            filtered_links = []
            for link in message_links:
                if not (
                    link.startswith("https://mmg-fna.whatsapp.net/")
                    or link.startswith("https://mmg.whatsapp.net/")
                ):
                    filtered_links.append(link)

            # Add all the links found to the record
            if filtered_links or (message.get("ZTEXT") or "").strip() == "":
                message["links"] = list(set(filtered_links))
            self.results.append(message)

        total_messages = len(self.results)
        lid_map = self._extract_lid_pairs(cur)
        total_sessions = self._extract_chat_sessions(cur, lid_map)

        cur.close()
        conn.close()

        self.log.info(
            "Extracted a total of %d WhatsApp messages, %d chat sessions "
            "and %d LID-phone number pairs",
            total_messages,
            total_sessions,
            len(lid_map),
        )

    def _find_lid_db_path(self) -> Optional[str]:
        for backup_id in WHATSAPP_LID_BACKUP_IDS:
            file_path = self._get_backup_file_from_id(backup_id)
            if file_path and os.path.exists(file_path):
                return file_path
        for found_path in self._get_fs_files_from_patterns(
            WHATSAPP_LID_ROOT_PATHS
        ):
            return found_path
        return None

    def _extract_lid_pairs(self, chat_cur: sqlite3.Cursor) -> Dict[str, str]:
        """Extract the LID to phone number mapping from the dedicated
        LID.sqlite database, falling back to the same table in
        ChatStorage.sqlite. Returns a map of LID digits to phone number
        digits."""
        rows = []
        lid_db_path = self._find_lid_db_path()
        if lid_db_path:
            self.log.info(
                "Found WhatsApp LID database at path: %s", lid_db_path
            )
            lid_conn = self._open_sqlite_db(lid_db_path)
            try:
                lid_cur = lid_conn.cursor()
                lid_cur.execute(LID_PAIRS_QUERY)
                rows = lid_cur.fetchall()
                lid_cur.close()
            except sqlite3.DatabaseError as exc:
                self.log.warning(
                    "Unable to extract WhatsApp LID-phone number pairs: %s",
                    exc,
                )
            finally:
                lid_conn.close()
        else:
            try:
                chat_cur.execute(LID_PAIRS_QUERY)
                rows = chat_cur.fetchall()
            except sqlite3.OperationalError:
                self.log.info(
                    "No WhatsApp LID database found in this backup or "
                    "filesystem dump: LID chat identifiers cannot be "
                    "resolved to phone numbers"
                )

        lid_map: Dict[str, str] = {}
        for lid, phone_number, pair_timestamp in rows:
            record = {
                "record_type": "lid_phone_number_pair",
                "lid": lid,
                "phone_number": phone_number,
                "pair_timestamp": (
                    convert_mactime_to_iso(pair_timestamp) or None
                )
                if pair_timestamp
                else None,
            }
            self.results.append(record)

            if lid and phone_number:
                lid_digits = str(lid).split("@")[0]
                phone_digits = str(phone_number).split("@")[0].lstrip("+")
                lid_map[lid_digits] = phone_digits

        return lid_map

    def _extract_chat_sessions(
        self, cur: sqlite3.Cursor, lid_map: Dict[str, str]
    ) -> int:
        """Extract one record per chat session with the first and last
        interaction dates of each conversation."""
        try:
            cur.execute(CHAT_SESSIONS_QUERY)
        except sqlite3.OperationalError as exc:
            self.log.warning(
                "Unable to extract WhatsApp chat sessions: %s", exc
            )
            return 0

        names = [description[0] for description in cur.description]

        total_sessions = 0
        for row in cur.fetchall():
            session = dict(zip(names, row))
            session["record_type"] = "chat_session"

            session["partner_resolved_phone_number"] = None
            jid = session.get("contact_jid") or ""
            if jid.endswith("@lid"):
                phone_digits = lid_map.get(jid.split("@")[0])
                if phone_digits:
                    session["partner_resolved_phone_number"] = (
                        f"+{phone_digits}"
                    )

            for field in CHAT_SESSION_DATE_FIELDS:
                if session.get(field):
                    session[field] = (
                        convert_mactime_to_iso(session[field]) or None
                    )
                else:
                    session[field] = None

            self.results.append(session)
            total_sessions += 1

        return total_sessions
