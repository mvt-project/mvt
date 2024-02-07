# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from base64 import b64encode
from typing import Optional, Union

from mvt.common.utils import convert_mactime_to_iso

from ..base import IOSExtraction

SMS_BACKUP_IDS = [
    "3d0d7e5fb2ce288813306e4d4636395e047a3d28",
]
SMS_ROOT_PATHS = [
    "private/var/mobile/Library/SMS/sms.db",
]


class SMSAttachments(IOSExtraction):
    """This module extracts all info about SMS/iMessage attachments."""

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

    def serialize(self, record: dict) -> Union[dict, list]:
        return {
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": "sms_attachment",
            "data": f"{record['service']}: Attachment "
            f"'{record['transfer_name']}' {record['direction']} "
            f"from {record['phone_number']} "
            f"with {record['total_bytes']} bytes "
            f"(is_sticker: {record['is_sticker']}, "
            f"has_user_info: {record['has_user_info']})",
        }

    def check_indicators(self) -> None:
        for attachment in self.results:
            # Check for known malicious filenames.
            if self.indicators and self.indicators.check_file_path(
                attachment["filename"]
            ):
                self.detected.append(attachment)

            if (
                attachment["filename"].startswith("/var/tmp/")
                and attachment["filename"].endswith("-1")
                and attachment["direction"] == "received"
            ):
                self.log.warning(
                    "Suspicious iMessage attachment %s on %s",
                    attachment["filename"],
                    attachment["isodate"],
                )
                self.detected.append(attachment)

    def run(self) -> None:
        self._find_ios_database(backup_ids=SMS_BACKUP_IDS, root_paths=SMS_ROOT_PATHS)
        self.log.info("Found SMS database at path: %s", self.file_path)

        conn = self._open_sqlite_db(self.file_path)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                attachment.ROWID as "attachment_id",
                attachment.*,
                message.service as "service",
                handle.id as "phone_number"
            FROM attachment
            LEFT JOIN message_attachment_join ON
                message_attachment_join.attachment_id = attachment.ROWID
            LEFT JOIN message ON
                message.ROWID = message_attachment_join.message_id
            LEFT JOIN handle ON handle.ROWID = message.handle_id;
        """
        )
        names = [description[0] for description in cur.description]

        for item in cur:
            attachment = {}
            for index, value in enumerate(item):
                if (
                    names[index]
                    in [
                        "user_info",
                        "sticker_user_info",
                        "attribution_info",
                        "ck_server_change_token_blob",
                        "sr_ck_server_change_token_blob",
                    ]
                ) and value:
                    value = b64encode(value).decode()
                attachment[names[index]] = value

            attachment["isodate"] = convert_mactime_to_iso(attachment["created_date"])
            attachment["start_date"] = convert_mactime_to_iso(attachment["start_date"])
            attachment["direction"] = (
                "sent" if attachment["is_outgoing"] == 1 else "received"
            )
            attachment["has_user_info"] = attachment["user_info"] is not None
            attachment["service"] = attachment["service"] or "Unknown"
            attachment["filename"] = attachment["filename"] or "NULL"
            self.results.append(attachment)

        cur.close()
        conn.close()

        self.log.info("Extracted a total of %d SMS attachments", len(self.results))
