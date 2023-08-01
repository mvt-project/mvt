# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import sqlite3
import fnmatch
from typing import Optional, Union

from mvt.common.utils import check_for_links, convert_mactime_to_iso

from ..base import IOSExtraction

VIBER_BACKUP_IDS = [
    "83b9310399a905c7781f95580174f321cd18fd97",
]
VIBER_ROOT_PATHS = [
    "private/var/mobile/Containers/Shared/AppGroup/*/viber-database.sqlite",
]


class Viber(IOSExtraction):

    """This module extracts all Viber messages and links from an IOS backup."""

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
        """Serialize data about the record."""
        text = record.get("ZTEXT", "").replace("\n", "\\n")
        links_text = ""
        if record.get("links"):
            links_text = " - Embedded links: " + ", ".join(record["links"])

        return {
            "timestamp": record.get("isodate"),
            "module": self.__class__.__name__,
            "event": "message",
            "data": f"'{text}' from {record.get('ZPHONE', 'Unknown')}{links_text}",
        }

    def check_indicators(self) -> None:
        """Check domains in the results list against provided IOCs."""
        if not self.indicators:
            return
        for result in self.results:
            ioc = self.indicators.check_domains(result.get("links", []))
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)

    def connect_to_database(self) -> None:
        """Attempt connection to the Viber database."""
        self._find_ios_database(
            backup_ids=VIBER_BACKUP_IDS, root_paths=VIBER_ROOT_PATHS
        )
        self.log.info("Found Viber database at path: %s", self.file_path)

        self.conn = sqlite3.connect(self.file_path)
        self.cur = self.conn.cursor()

    def query_messages(self) -> None:
        """Query records from the Viber messages table
        joined with the phone number table.
        """
        self.cur.execute(
            """
            SELECT
                ZVIBERMESSAGE.*,
                ZPHONENUMBER.ZPHONE
            FROM ZVIBERMESSAGE
            LEFT JOIN ZPHONENUMBER ON
                ZPHONENUMBER.Z_PK = ZVIBERMESSAGE.Z_PK;
        """
        )
        # Get column names
        self.col_names = [description[0] for description in self.cur.description]

    def extract_messages(self) -> None:
        """Extract messages and links from the query and add findings
        to final results array.
        """
        # Loop through each message record
        for message_row in self.cur:
            # Create a dict for the current message containing all the keys & values
            message = {}
            for index, value in enumerate(message_row):
                message[self.col_names[index]] = value

            # Add an iso date key to the dict
            message["isodate"] = convert_mactime_to_iso(message.get("ZDATE"))
            # If record has no "ZTEXT" then create it with an empty string value
            message["ZTEXT"] = message["ZTEXT"] if message["ZTEXT"] else ""

            # Extract links from the Viber message.
            message_links = []
            fields_with_links = [
                "ZTEXT",
                "ZCLIENTMETADATA",
            ]
            for field in fields_with_links:
                # If message contains a link, add it to the message_links list
                if message.get(field):
                    message_links.extend(check_for_links(message.get(field, "")))

            # Filter out internal Viber URLs from the final filtered links list
            self.filter_out_trusted_links(message_links)

            # Add all the links found to the "list" key in the message dictionary
            if self.filtered_links or (message.get("ZTEXT") or "").strip() == "":
                message["links"] = list(set(self.filtered_links))
            # Append current message to the results array
            self.results.append(message)

    def filter_out_trusted_links(self, message_links) -> None:
        """Filter out Viber internal URLs from list of message links.
        Operating under the assumption that links
        from the official Viber domain are free of malware.
        """
        # TODO: Once we have more Viber message data verify that this wildcard combo
        # is acceptable for filtering out internal URLs
        self.filtered_links = []
        for link in message_links:
            if not (fnmatch.fnmatch(link, "*.viber.com/*")):
                self.filtered_links.append(link)

    def run(self) -> None:
        self.connect_to_database()

        self.query_messages()

        self.extract_messages()

        self.cur.close()
        self.conn.close()

        self.log.info("Extracted a total of %d Viber messages", len(self.results))
