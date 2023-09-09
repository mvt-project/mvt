# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import base64
import logging
import os
import sqlite3
from typing import Optional, Union

from mvt.common.utils import check_for_links, convert_unix_to_iso

from .base import AndroidExtraction

WHATSAPP_PATH = "data/data/com.whatsapp/databases/msgstore.db"


class Whatsapp(AndroidExtraction):
    """This module extracts all WhatsApp messages containing links."""

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
        text = record["data"].replace("\n", "\\n")
        return {
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": f"whatsapp_msg_{record['direction']}",
            "data": f'"{text}"',
        }

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for message in self.results:
            if "data" not in message:
                continue

            message_links = check_for_links(message["data"])
            if self.indicators.check_domains(message_links):
                self.detected.append(message)

    def _parse_db(self, db_path: str) -> None:
        """Parse an Android msgstore.db WhatsApp database file.

        :param db_path: Path to the Android WhatsApp database file to process

        """
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT * FROM messages;
        """
        )
        names = [description[0] for description in cur.description]

        messages = []
        for item in cur:
            message = {}
            for index, value in enumerate(item):
                message[names[index]] = value

            if not message["data"]:
                continue

            message["direction"] = "send" if message["key_from_me"] == 1 else "received"
            message["isodate"] = convert_unix_to_iso(message["timestamp"])

            # If we find links in the messages or if they are empty we add them
            # to the list.
            if check_for_links(message["data"]) or message["data"].strip() == "":
                if message.get("thumb_image"):
                    message["thumb_image"] = base64.b64encode(message["thumb_image"])

                messages.append(message)

        cur.close()
        conn.close()

        self.log.info(
            "Extracted a total of %d WhatsApp messages containing links", len(messages)
        )
        self.results = messages

    def run(self) -> None:
        self._adb_connect()

        try:
            self._adb_process_file(os.path.join("/", WHATSAPP_PATH), self._parse_db)
        except Exception as exc:
            self.log.error(exc)

        self._adb_disconnect()
