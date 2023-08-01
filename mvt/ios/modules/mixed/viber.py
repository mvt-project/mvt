# Mobile Verification Toolkit (MVT)
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import sqlite3
from typing import Optional, Union

from mvt.common.utils import check_for_links, convert_mactime_to_iso

from ..base import IOSExtraction

VIBER_BACKUP_IDS = [
    "83b9310399a905c7781f95580174f321cd18fd97",
]
VIBER_ROOT_PATHS = [
    "path/to/viber/db/viber-database.sqlite",
]


class Viber(IOSExtraction):
    """This module extracts all Viber messages containing links."""

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
        text = record.get("text", "").replace("\n", "\\n")
        links_text = ""
        if record.get("links"):
            links_text = " - Embedded links: " + ", ".join(record["links"])

        return {
            "timestamp": record.get("isodate"),
            "module": self.__class__.__name__,
            "event": "message",
            "data": f"'{text}' {links_text}",
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
            backup_ids=VIBER_BACKUP_IDS, root_paths=VIBER_ROOT_PATHS
        )
        self.log.info("Found Viber database at path: %s", self.file_path)
        try:
            conn = sqlite3.connect(self.file_path)
            cur = conn.cursor()
            cur.execute("select ZDATE, ZTEXT from ZVIBERMESSAGE;")
        except:
            conn.close()
            raise
        for query_result in cur:
            message_text = query_result[1]
            message_links = check_for_links(message_text)
            if message_links:
                message = {}
                message["text"] = message_text
                message["isodate"] = convert_mactime_to_iso(query_result[0])
                message["links"] = message_links
                self.results.append(message)
        cur.close()
        conn.close()
