# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional, Union

from mvt.common.utils import check_for_links, convert_mactime_to_iso

from ..base import IOSExtraction

WHATSAPP_BACKUP_IDS = [
    "7c7fba66680ef796b916b067077cc246adacf01d",
]
WHATSAPP_ROOT_PATHS = [
    "private/var/mobile/Containers/Shared/AppGroup/*/ChatStorage.sqlite",
]


class Whatsapp(IOSExtraction):
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
        text = record.get("ZTEXT", "").replace("\n", "\\n")
        links_text = ""
        if record.get("links"):
            links_text = " - Embedded links: " + ", ".join(record["links"])

        return {
            "timestamp": record.get("isodate"),
            "module": self.__class__.__name__,
            "event": "message",
            "data": f"'{text}' from {record.get('ZFROMJID', 'Unknown')}{links_text}",
        }

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_domains(result.get("links", []))
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)

    def run(self) -> None:
        self._find_ios_database(
            backup_ids=WHATSAPP_BACKUP_IDS, root_paths=WHATSAPP_ROOT_PATHS
        )
        self.log.info("Found WhatsApp database at path: %s", self.file_path)

        conn = self._open_sqlite_db(self.file_path)
        cur = conn.cursor()

        # Query all messages and join tables which can contain media attachments
        # and links.
        cur.execute(
            """
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
            LEFT JOIN ZWAMESSAGEDATAITEM ON
                ZWAMESSAGEDATAITEM.ZMESSAGE = ZWAMESSAGE.Z_PK;
        """
        )
        names = [description[0] for description in cur.description]

        for message_row in cur:
            message = {}
            for index, value in enumerate(message_row):
                message[names[index]] = value

            message["isodate"] = convert_mactime_to_iso(message.get("ZMESSAGEDATE"))
            message["ZTEXT"] = message["ZTEXT"] if message["ZTEXT"] else ""

            # Extract links from the WhatsApp message. URLs can be stored in
            # multiple fields/columns.
            # Check each of them!
            message_links = []
            fields_with_links = [
                "ZTEXT",
                "ZMATCHEDTEXT",
                "ZMEDIAURL",
                "ZCONTENT1",
                "ZCONTENT2",
            ]
            for field in fields_with_links:
                if message.get(field):
                    message_links.extend(check_for_links(message.get(field, "")))

            # Remove WhatsApp internal media URLs.
            filtered_links = []
            for link in message_links:
                if not (
                    link.startswith("https://mmg-fna.whatsapp.net/")
                    or link.startswith("https://mmg.whatsapp.net/")
                ):
                    filtered_links.append(link)

            # Add all the links found to the record
            if filtered_links or (message.get("ZTEXT") or "").strip() == "":
                message["links"] = list(set(filtered_links))
            self.results.append(message)

        cur.close()
        conn.close()

        self.log.info("Extracted a total of %d WhatsApp messages", len(self.results))
