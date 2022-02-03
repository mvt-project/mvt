# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import base64
import logging
import os
import sqlite3

from mvt.common.utils import check_for_links, convert_timestamp_to_iso

from .base import AndroidExtraction

log = logging.getLogger(__name__)

WHATSAPP_PATH = "data/data/com.whatsapp/databases/msgstore.db"


class Whatsapp(AndroidExtraction):
    """This module extracts all WhatsApp messages containing links."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 serial=None, fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record):
        text = record["data"].replace("\n", "\\n")
        return {
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": f"whatsapp_msg_{record['direction']}",
            "data": f"\"{text}\""
        }

    def check_indicators(self):
        if not self.indicators:
            return

        for message in self.results:
            if "data" not in message:
                continue

            message_links = check_for_links(message["data"])
            if self.indicators.check_domains(message_links):
                self.detected.append(message)

    def _parse_db(self, db_path):
        """Parse an Android msgstore.db WhatsApp database file.

        :param db_path: Path to the Android WhatsApp database file to process

        """
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM messages;
        """)
        names = [description[0] for description in cur.description]

        messages = []
        for item in cur:
            message = {}
            for index, value in enumerate(item):
                message[names[index]] = value

            if not message["data"]:
                continue

            message["direction"] = ("send" if message["key_from_me"] == 1 else "received")
            message["isodate"] = convert_timestamp_to_iso(message["timestamp"])

            # If we find links in the messages or if they are empty we add them to the list.
            if check_for_links(message["data"]) or message["data"].strip() == "":
                if (message.get('thumb_image') is not None):
                    message['thumb_image'] = base64.b64encode(message['thumb_image'])
                messages.append(message)

        cur.close()
        conn.close()

        log.info("Extracted a total of %d WhatsApp messages containing links", len(messages))
        self.results = messages

    def run(self):
        try:
            self._adb_process_file(os.path.join("/", WHATSAPP_PATH), self._parse_db)
        except Exception as e:
            self.log.error(e)
