# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 MVT Project Developers.
# See the file 'LICENSE' for usage and copying permissions, or find a copy at
#   https://github.com/mvt-project/mvt/blob/main/LICENSE

import sqlite3
from base64 import b64encode

from mvt.common.utils import check_for_links
from mvt.common.utils import convert_mactime_to_unix, convert_timestamp_to_iso

from .base import IOSExtraction

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

        for message in self.results:
            if not "text" in message:
                continue

            message_links = check_for_links(message["text"])
            if self.indicators.check_domains(message_links):
                self.detected.append(message)

    def run(self):
        self._find_ios_database(backup_ids=SMS_BACKUP_IDS, root_paths=SMS_ROOT_PATHS)
        self.log.info("Found SMS database at path: %s", self.file_path)

        conn = sqlite3.connect(self.file_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT
                message.*,
                handle.id as "phone_number"
            FROM message, handle
            WHERE handle.rowid = message.handle_id;
        """)
        names = [description[0] for description in cur.description]

        for item in cur:
            message = dict()
            for index, value in enumerate(item):
                # We base64 escape some of the attributes that could contain
                # binary data.
                if (names[index] == "attributedBody" or
                    names[index] == "payload_data" or
                    names[index] == "message_summary_info") and value:
                    value = b64encode(value).decode()

                # We store the value of each column under the proper key.
                message[names[index]] = value

            # We convert Mac's ridiculous timestamp format.
            message["isodate"] = convert_timestamp_to_iso(convert_mactime_to_unix(message["date"]))
            message["direction"] = ("sent" if message["is_from_me"] == 1 else "received")

            # Sometimes "text" is None instead of empty string.
            if message["text"] is None:
                message["text"] = ""

            # Extract links from the SMS message.
            message_links = check_for_links(message["text"])

            # If we find links in the messages or if they are empty we add them to the list.
            if message_links or message["text"].strip() == "":
                self.results.append(message)

        cur.close()
        conn.close()

        self.log.info("Extracted a total of %d SMS messages containing links", len(self.results))
