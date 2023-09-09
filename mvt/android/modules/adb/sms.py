# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
import sqlite3
from typing import Optional, Union

from mvt.android.parsers.backup import AndroidBackupParsingError, parse_tar_for_sms
from mvt.common.module import InsufficientPrivileges
from mvt.common.utils import check_for_links, convert_unix_to_iso

from .base import AndroidExtraction

SMS_BUGLE_PATH = "data/data/com.google.android.apps.messaging/databases/bugle_db"
SMS_BUGLE_QUERY = """
SELECT
    ppl.normalized_destination AS address,
    p.timestamp AS timestamp,
CASE WHEN m.sender_id IN
(SELECT _id FROM participants WHERE contact_id=-1)
THEN 2 ELSE 1 END incoming, p.text AS body
FROM messages m, conversations c, parts p,
        participants ppl, conversation_participants cp
WHERE (m.conversation_id = c._id)
    AND (m._id = p.message_id)
    AND (cp.conversation_id = c._id)
    AND (cp.participant_id = ppl._id);
"""

SMS_MMSSMS_PATH = "data/data/com.android.providers.telephony/databases/mmssms.db"
SMS_MMSMS_QUERY = """
SELECT
    address AS address,
    date_sent AS timestamp,
    type as incoming,
    body AS body
FROM sms;
"""


class SMS(AndroidExtraction):
    """This module extracts all SMS messages."""

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

        self.sms_db_type = 0

    def serialize(self, record: dict) -> Union[dict, list]:
        body = record["body"].replace("\n", "\\n")
        return {
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": f"sms_{record['direction']}",
            "data": f"{record.get('address', 'unknown source')}: \"{body}\"",
        }

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for message in self.results:
            if "body" not in message:
                continue

            message_links = message.get("links", [])
            if message_links == []:
                message_links = check_for_links(message["body"])

            if self.indicators.check_domains(message_links):
                self.detected.append(message)

    def _parse_db(self, db_path: str) -> None:
        """Parse an Android bugle_db SMS database file.

        :param db_path: Path to the Android SMS database file to process

        """
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        if self.sms_db_type == 1:
            cur.execute(SMS_BUGLE_QUERY)
        elif self.sms_db_type == 2:
            cur.execute(SMS_MMSMS_QUERY)

        names = [description[0] for description in cur.description]

        for item in cur:
            message = {}
            for index, value in enumerate(item):
                message[names[index]] = value

            message["direction"] = "received" if message["incoming"] == 1 else "sent"
            message["isodate"] = convert_unix_to_iso(message["timestamp"])

            # Extract links in the message body
            links = check_for_links(message["body"])
            message["links"] = links

            self.results.append(message)

        cur.close()
        conn.close()

        self.log.info("Extracted a total of %d SMS messages", len(self.results))

    def _extract_sms_adb(self) -> None:
        """Use the Android backup command to extract SMS data from the native
        SMS app.

        It is crucial to use the under-documented "-nocompress" flag to disable
        the non-standard Java compression algorithm. This module only supports
        an unencrypted ADB backup.
        """
        backup_tar = self._generate_backup("com.android.providers.telephony")
        if not backup_tar:
            return

        try:
            self.results = parse_tar_for_sms(backup_tar)
        except AndroidBackupParsingError:
            self.log.info(
                "Impossible to read SMS from the Android Backup, "
                "please extract the SMS and try extracting it with "
                "Android Backup Extractor"
            )
            return

        self.log.info("Extracted a total of %d SMS messages", len(self.results))

    def run(self) -> None:
        self._adb_connect()

        try:
            if self._adb_check_file_exists(os.path.join("/", SMS_BUGLE_PATH)):
                self.sms_db_type = 1
                self._adb_process_file(
                    os.path.join("/", SMS_BUGLE_PATH), self._parse_db
                )
            elif self._adb_check_file_exists(os.path.join("/", SMS_MMSSMS_PATH)):
                self.sms_db_type = 2
                self._adb_process_file(
                    os.path.join("/", SMS_MMSSMS_PATH), self._parse_db
                )

            self._adb_disconnect()
            return
        except InsufficientPrivileges:
            pass

        self.log.info(
            "No SMS database found. Trying extraction of SMS data "
            "using Android backup feature."
        )
        self._extract_sms_adb()

        self._adb_disconnect()
