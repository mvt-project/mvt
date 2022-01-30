# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
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
        links_text = ""
        if record["links"]:
            links_text = " - Embedded links: " + ", ".join(record["links"])

        return {
            "timestamp": record.get("isodate"),
            "module": self.__class__.__name__,
            "event": "message",
            "data": f"\'{text}\' from {record.get('ZFROMJID', 'Unknown')}{links_text}",
        }

    def check_indicators(self):
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_domains(result.get("links", []))
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)

    def run(self):
        self._find_ios_database(backup_ids=WHATSAPP_BACKUP_IDS,
                                root_paths=WHATSAPP_ROOT_PATHS)
        log.info("Found WhatsApp database at path: %s", self.file_path)

        conn = sqlite3.connect(self.file_path)
        cur = conn.cursor()

        # Query all messages and join tables which can contain media attachments and links
        cur.execute("""
            SELECT
                ZWAMESSAGE.*,
                ZWAMEDIAITEM.ZAUTHORNAME,
                ZWAMEDIAITEM.ZMEDIAURL,
                ZWAMESSAGEDATAITEM.ZCONTENT1,
                ZWAMESSAGEDATAITEM.ZCONTENT2,
                ZWAMESSAGEDATAITEM.ZMATCHEDTEXT,
                ZWAMESSAGEDATAITEM.ZSUMMARY,
                ZWAMESSAGEDATAITEM.ZTITLE
            FROM ZWAMESSAGE
            LEFT JOIN ZWAMEDIAITEM ON ZWAMEDIAITEM.ZMESSAGE = ZWAMESSAGE.Z_PK
            LEFT JOIN ZWAMESSAGEDATAITEM ON ZWAMESSAGEDATAITEM.ZMESSAGE = ZWAMESSAGE.Z_PK;
        """)
        names = [description[0] for description in cur.description]

        for message_row in cur:
            message = {}
            for index, value in enumerate(message_row):
                message[names[index]] = value

            message["isodate"] = convert_timestamp_to_iso(convert_mactime_to_unix(message.get("ZMESSAGEDATE")))
            message["ZTEXT"] = message["ZTEXT"] if message["ZTEXT"] else ""

            # Extract links from the WhatsApp message. URLs can be stored in multiple fields/columns.
            # Check each of them!
            message_links = []
            fields_with_links = ["ZTEXT", "ZMATCHEDTEXT", "ZMEDIAURL", "ZCONTENT1", "ZCONTENT2"]
            for field in fields_with_links:
                if message.get(field):
                    message_links.extend(check_for_links(message.get(field, "")))

            # Remove WhatsApp internal media URLs.
            filtered_links = []
            for link in message_links:
                if not (link.startswith("https://mmg-fna.whatsapp.net/") or link.startswith("https://mmg.whatsapp.net/")):
                    filtered_links.append(link)

            # If we find messages with links, or if there's an empty message we add it to the results list.
            if filtered_links or (message.get("ZTEXT") or "").strip() == "":
                message["links"] = list(set(filtered_links))
                self.results.append(message)

        cur.close()
        conn.close()

        log.info("Extracted a total of %d WhatsApp messages containing links", len(self.results))
