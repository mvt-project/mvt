# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 MVT Project Developers.
# See the file 'LICENSE' for usage and copying permissions, or find a copy at
#   https://github.com/mvt-project/mvt/blob/main/LICENSE

import os
import sqlite3
import logging

from .base import AndroidExtraction
from mvt.common.utils import convert_timestamp_to_iso, check_for_links

log = logging.getLogger(__name__)

SMS_PATH = "data/data/com.google.android.apps.messaging/databases/bugle_db"
SMS_PATH_2 = "data/data/com.android.providers.telephony/databases/mmssms.db"
sql_command_1 = """
SELECT 
    ppl.normalized_destination AS number,
    p.timestamp AS timestamp,
CASE WHEN m.sender_id IN 
(SELECT _id FROM participants WHERE contact_id=-1)
THEN 2 ELSE 1 END incoming, p.text AS text 
FROM messages m, conversations c, parts p,
        participants ppl, conversation_participants cp
WHERE (m.conversation_id = c._id)
    AND (m._id = p.message_id)
    AND (cp.conversation_id = c._id)
    AND (cp.participant_id = ppl._id);
"""
sql_command_2 = """
SELECT 
    address AS number,
    date_sent AS timestamp,
    type as incoming,
    body AS text 
FROM sms;
"""

class SMS(AndroidExtraction):
    """This module extracts all SMS messages containing links."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record):
        text = record["text"].replace("\n", "\\n")
        return {
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": f"sms_{record['direction']}",
            "data": f"{record['number']}: \"{text}\""
        }

    def check_indicators(self):
        if not self.indicators:
            return

        for message in self.results:
            if not "text" in message:
                continue

            message_links = check_for_links(message["text"])
            if self.indicators.check_domains(message_links):
                self.detected.append(message)

    def _parse_db(self, db_path):
        """Parse an Android bugle_db SMS database file.
        :param db_path: Path to the Android SMS database file to process
        :param sql_command: SQL command to execute
        """
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        if (self.SMS_DB_TYPE == 1):
            cur.execute(sql_command_1)
        elif (self.SMS_DB_TYPE == 2):
            cur.execute(sql_command_2)

        names = [description[0] for description in cur.description]

        for item in cur:
            message = dict()
            for index, value in enumerate(item):
                message[names[index]] = value

            message["direction"] = ("received" if message["incoming"] == 1 else "sent")
            message["isodate"] = convert_timestamp_to_iso(message["timestamp"])

            # If we find links in the messages or if they are empty we add
            # them to the list of results.
            if check_for_links(message["text"]) or message["text"].strip() == "":
                self.results.append(message)

        cur.close()
        conn.close()

        log.info("Extracted a total of %d SMS messages containing links", len(self.results))

    def run(self):
        # Checking the SMS database path
        try:
            if (self._adb_check_file_exists(os.path.join("/", SMS_PATH))):
                self.SMS_DB_TYPE = 1
                self._adb_process_file(os.path.join("/", SMS_PATH), self._parse_db)
            elif (self._adb_check_file_exists(os.path.join("/", SMS_PATH_2))):
                self.SMS_DB_TYPE = 2
                self._adb_process_file(os.path.join("/", SMS_PATH_2), self._parse_db)
            else:
                self.log.error("No SMS database found")
        except Exception as e:
            self.log.error(e)
