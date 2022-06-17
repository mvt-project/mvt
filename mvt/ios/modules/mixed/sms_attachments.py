# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import sqlite3
from base64 import b64encode

from mvt.common.utils import convert_mactime_to_unix, convert_timestamp_to_iso

from ..base import IOSExtraction

SMS_BACKUP_IDS = [
    "3d0d7e5fb2ce288813306e4d4636395e047a3d28",
]
SMS_ROOT_PATHS = [
    "private/var/mobile/Library/SMS/sms.db",
]


class SMSAttachments(IOSExtraction):
    """This module extracts all info about SMS/iMessage attachments."""

    def __init__(self, file_path: str = None, target_path: str = None,
                 results_path: str = None, fast_mode: bool = False,
                 log: logging.Logger = None, results: list = []) -> None:
        super().__init__(file_path=file_path, target_path=target_path,
                         results_path=results_path, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record: dict) -> None:
        return {
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": "sms_attachment",
            "data": f"{record['service']}: Attachment '{record['transfer_name']}' {record['direction']} from {record['phone_number']} "
                    f"with {record['total_bytes']} bytes (is_sticker: {record['is_sticker']}, has_user_info: {record['has_user_info']})"
        }

    def run(self) -> None:
        self._find_ios_database(backup_ids=SMS_BACKUP_IDS,
                                root_paths=SMS_ROOT_PATHS)
        self.log.info("Found SMS database at path: %s", self.file_path)

        conn = sqlite3.connect(self.file_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT
                attachment.ROWID as "attachment_id",
                attachment.*,
                message.service as "service",
                handle.id as "phone_number"
            FROM attachment
            LEFT JOIN message_attachment_join ON message_attachment_join.attachment_id = attachment.ROWID
            LEFT JOIN message ON message.ROWID = message_attachment_join.message_id
            LEFT JOIN handle ON handle.ROWID = message.handle_id;
        """)
        names = [description[0] for description in cur.description]

        for item in cur:
            attachment = {}
            for index, value in enumerate(item):
                if (names[index] in ["user_info", "sticker_user_info",
                                     "attribution_info",
                                     "ck_server_change_token_blob",
                                     "sr_ck_server_change_token_blob"]) and value:
                    value = b64encode(value).decode()
                attachment[names[index]] = value

            attachment["isodate"] = convert_timestamp_to_iso(convert_mactime_to_unix(attachment["created_date"]))
            attachment["start_date"] = convert_timestamp_to_iso(convert_mactime_to_unix(attachment["start_date"]))
            attachment["direction"] = ("sent" if attachment["is_outgoing"] == 1 else "received")
            attachment["has_user_info"] = attachment["user_info"] is not None
            attachment["service"] = attachment["service"] or "Unknown"
            attachment["filename"] = attachment["filename"] or "NULL"

            if (attachment["filename"].startswith("/var/tmp/") and attachment["filename"].endswith("-1")
                    and attachment["direction"] == "received"):
                self.log.warn(f"Suspicious iMessage attachment '{attachment['filename']}' on {attachment['isodate']}")
                self.detected.append(attachment)

            self.results.append(attachment)

        cur.close()
        conn.close()

        self.log.info("Extracted a total of %d SMS attachments", len(self.results))
