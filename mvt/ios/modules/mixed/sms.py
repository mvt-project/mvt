# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import sqlite3
from base64 import b64encode

from mvt.common.utils import (check_for_links, convert_mactime_to_unix,
                              convert_timestamp_to_iso)

from ..base import IOSExtraction

SMS_BACKUP_IDS = [
    "3d0d7e5fb2ce288813306e4d4636395e047a3d28",
]
SMS_ROOT_PATHS = [
    "private/var/mobile/Library/SMS/sms.db",
]


class SMS(IOSExtraction):
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
            "event": "sms_received",
            "data": f"{record['service']}: {record['guid']} \"{text}\" from {record['phone_number']} ({record['account']})"
        }

    def check_indicators(self):
        if not self.indicators:
            return

        for result in self.results:
            message_links = check_for_links(result.get("text", ""))
            ioc = self.indicators.check_domains(message_links)
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)

    def run(self):
        self._find_ios_database(backup_ids=SMS_BACKUP_IDS,
                                root_paths=SMS_ROOT_PATHS)
        self.log.info("Found SMS database at path: %s", self.file_path)

        try:
            conn = sqlite3.connect(self.file_path)
            cur = conn.cursor()
            cur.execute("""
                SELECT
                    message.*,
                    handle.id as "phone_number"
                FROM message, handle
                WHERE handle.rowid = message.handle_id;
            """)
            # Force the query early to catch database issues
            items = list(cur)
        except sqlite3.DatabaseError as e:
            conn.close()
            if "database disk image is malformed" in str(e):
                self._recover_sqlite_db_if_needed(self.file_path, forced=True)
                conn = sqlite3.connect(self.file_path)
                cur = conn.cursor()
                cur.execute("""
                    SELECT
                        message.*,
                        handle.id as "phone_number"
                    FROM message, handle
                    WHERE handle.rowid = message.handle_id;
                """)
                items = list(cur)
            else:
                raise e
        names = [description[0] for description in cur.description]

        for item in items:
            message = {}
            for index, value in enumerate(item):
                # We base64 escape some of the attributes that could contain
                # binary data.
                if (names[index] == "attributedBody" or names[index] == "payload_data"
                        or names[index] == "message_summary_info") and value:
                    value = b64encode(value).decode()

                # We store the value of each column under the proper key.
                message[names[index]] = value

            # We convert Mac's ridiculous timestamp format.
            message["isodate"] = convert_timestamp_to_iso(convert_mactime_to_unix(message["date"]))
            message["direction"] = ("sent" if message.get("is_from_me", 0) == 1 else "received")

            # Sometimes "text" is None instead of empty string.
            if not message.get("text", None):
                message["text"] = ""

            if message.get("text", "").startswith("ALERT: State-sponsored attackers may be targeting your iPhone"):
                self.log.warn("Apple warning about state-sponsored attack received on the %s", message["isodate"])
                self.results.append(message)
            else:
                # Extract links from the SMS message.
                message_links = check_for_links(message.get("text", ""))

                # If we find links in the messages or if they are empty we add them to the list.
                if message_links or message.get("text", "").strip() == "":
                    self.results.append(message)

        cur.close()
        conn.close()

        self.log.info("Extracted a total of %d SMS messages containing links", len(self.results))
