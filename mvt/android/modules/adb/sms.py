# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
import sqlite3

from mvt.android.parsers.backup import (AndroidBackupParsingError,
                                        parse_tar_for_sms)
from mvt.common.module import InsufficientPrivileges
from mvt.common.utils import check_for_links, convert_timestamp_to_iso

from .base import AndroidExtraction

log = logging.getLogger(__name__)

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
    """This module extracts all SMS messages containing links."""

    def __init__(self, file_path: str = None, target_path: str = None,
                 results_path: str = None, fast_mode: bool = False,
                 log: logging.Logger = None, results: list = []) -> None:
        super().__init__(file_path=file_path, target_path=target_path,
                         results_path=results_path, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record: dict) -> None:
        body = record["body"].replace("\n", "\\n")
        return {
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": f"sms_{record['direction']}",
            "data": f"{record.get('address', 'unknown source')}: \"{body}\""
        }

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for message in self.results:
            if "body" not in message:
                continue

            # TODO: check links exported from the body previously.
            message_links = check_for_links(message["body"])
            if self.indicators.check_domains(message_links):
                self.detected.append(message)

    def _parse_db(self, db_path: str) -> None:
        """Parse an Android bugle_db SMS database file.

        :param db_path: Path to the Android SMS database file to process

        """
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        if self.SMS_DB_TYPE == 1:
            cur.execute(SMS_BUGLE_QUERY)
        elif self.SMS_DB_TYPE == 2:
            cur.execute(SMS_MMSMS_QUERY)

        names = [description[0] for description in cur.description]

        for item in cur:
            message = {}
            for index, value in enumerate(item):
                message[names[index]] = value

            message["direction"] = ("received" if message["incoming"] == 1 else "sent")
            message["isodate"] = convert_timestamp_to_iso(message["timestamp"])

            # If we find links in the messages or if they are empty we add
            # them to the list of results.
            if check_for_links(message["body"]) or message["body"].strip() == "":
                self.results.append(message)

        cur.close()
        conn.close()

        log.info("Extracted a total of %d SMS messages containing links", len(self.results))

    def _extract_sms_adb(self) -> None:
        """Use the Android backup command to extract SMS data from the native SMS
        app.

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
            self.log.info("Impossible to read SMS from the Android Backup, please extract "\
                          "the SMS and try extracting it with Android Backup Extractor")
            return

        log.info("Extracted a total of %d SMS messages containing links", len(self.results))

    def run(self) -> None:
        try:
            if (self._adb_check_file_exists(os.path.join("/", SMS_BUGLE_PATH))):
                self.SMS_DB_TYPE = 1
                self._adb_process_file(os.path.join("/", SMS_BUGLE_PATH), self._parse_db)
            elif (self._adb_check_file_exists(os.path.join("/", SMS_MMSSMS_PATH))):
                self.SMS_DB_TYPE = 2
                self._adb_process_file(os.path.join("/", SMS_MMSSMS_PATH), self._parse_db)
            return
        except InsufficientPrivileges:
            pass

        self.log.warn("No SMS database found. Trying extraction of SMS data using " \
                      "Android backup feature.")
        self._extract_sms_adb()
