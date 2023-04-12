# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import sqlite3
from base64 import b64encode
from typing import Optional, Union

from mvt.common.utils import check_for_links, convert_mactime_to_iso

from ..base import IOSExtraction

SMS_BACKUP_IDS = [
    "3d0d7e5fb2ce288813306e4d4636395e047a3d28",
]
SMS_ROOT_PATHS = [
    "private/var/mobile/Library/SMS/sms.db",
]


class SMS(IOSExtraction):
    """This module extracts all SMS messages containing links."""

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        fast_mode: Optional[bool] = False,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[list] = None
    ) -> None:
        super().__init__(file_path=file_path, target_path=target_path,
                         results_path=results_path, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record: dict) -> Union[dict, list]:
        text = record["text"].replace("\n", "\\n")
        return {
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": "sms_received",
            "data": f"{record['service']}: {record['guid']} \"{text}\" "
                    f"from {record['phone_number']} ({record['account']})"
        }

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            message_links = result.get("links", [])
            # Making sure not link was ignored
            if message_links == []:
                message_links = check_for_links(result.get("text", ""))
            ioc = self.indicators.check_domains(message_links)
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)

    def run(self) -> None:
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
        except sqlite3.DatabaseError as exc:
            conn.close()
            if "database disk image is malformed" in str(exc):
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
                raise exc
        names = [description[0] for description in cur.description]

        for item in items:
            message = {}
            for index, value in enumerate(item):
                # We base64 escape some of the attributes that could contain
                # binary data.
                if (names[index] == "attributedBody"
                        or names[index] == "payload_data"
                        or names[index] == "message_summary_info") and value:
                    value = b64encode(value).decode()

                # We store the value of each column under the proper key.
                message[names[index]] = value

            # We convert Mac's ridiculous timestamp format.
            message["isodate"] = convert_mactime_to_iso(message["date"])
            message["direction"] = ("sent" if message.get("is_from_me", 0) == 1
                                        else "received")

            # Sometimes "text" is None instead of empty string.
            if not message.get("text", None):
                message["text"] = ""

            alert = "ALERT: State-sponsored attackers may be targeting your iPhone"
            if message.get("text", "").startswith(alert):
                self.log.warning("Apple warning about state-sponsored attack received on the %s",
                                 message["isodate"])
            else:
                # Extract links from the SMS message.
                message_links = check_for_links(message.get("text", ""))
                message["links"] = message_links

            self.results.append(message)

        cur.close()
        conn.close()

        self.log.info("Extracted a total of %d SMS messages",
                      len(self.results))
