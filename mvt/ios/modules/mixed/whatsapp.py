# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import sqlite3

from mvt.common.utils import (check_for_links, convert_mactime_to_unix,
                              convert_timestamp_to_iso)

from ..base import IOSExtraction

log = logging.getLogger(__name__)

WHATSAPP_BACKUP_IDS = [
    "7c7fba66680ef796b916b067077cc246adacf01d",
]
WHATSAPP_ROOT_PATHS = [
    "private/var/mobile/Containers/Shared/AppGroup/*/ChatStorage.sqlite",
]

class Whatsapp(IOSExtraction):
    """This module extracts all WhatsApp messages containing links."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record):
        text = record.get("ZTEXT", "").replace("\n", "\\n")
        return {
            "timestamp": record.get("isodate"),
            "module": self.__class__.__name__,
            "event": "message",
            "data": f"{text} from {record.get('ZFROMJID', 'Unknown')}",
        }

    def check_indicators(self):
        if not self.indicators:
            return

        for message in self.results:
            message_links = check_for_links(message.get("ZTEXT", ""))
            if self.indicators.check_domains(message_links):
                self.detected.append(message)

    def run(self):
        self._find_ios_database(backup_ids=WHATSAPP_BACKUP_IDS,
                                root_paths=WHATSAPP_ROOT_PATHS)
        log.info("Found WhatsApp database at path: %s", self.file_path)

        conn = sqlite3.connect(self.file_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM ZWAMESSAGE;")
        names = [description[0] for description in cur.description]

        for message in cur:
            new_message = {}
            for index, value in enumerate(message):
                new_message[names[index]] = value

            if not new_message.get("ZTEXT", None):
                continue

            # We convert Mac's silly timestamp again.
            new_message["isodate"] = convert_timestamp_to_iso(convert_mactime_to_unix(new_message.get("ZMESSAGEDATE")))

            # Extract links from the WhatsApp message.
            message_links = check_for_links(new_message["ZTEXT"])

            # If we find messages, or if there's an empty message we add it to the list.
            if new_message["ZTEXT"] and (message_links or new_message["ZTEXT"].strip() == ""):
                self.results.append(new_message)

        cur.close()
        conn.close()

        log.info("Extracted a total of %d WhatsApp messages containing links", len(self.results))
