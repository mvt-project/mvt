# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import sqlite3
from datetime import datetime

from mvt.common.utils import convert_timestamp_to_iso

from ..base import IOSExtraction

FIREFOX_HISTORY_BACKUP_IDS = [
    "2e57c396a35b0d1bcbc624725002d98bd61d142b",
]
FIREFOX_HISTORY_ROOT_PATHS = [
    "private/var/mobile/profile.profile/browser.db",
]


class FirefoxFavicon(IOSExtraction):
    """This module extracts all Firefox favicon"""

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
            "event": "firefox_history",
            "data": f"Firefox favicon {record['url']} when visiting {record['history_url']}",
        }

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_domain(result.get("url", ""))
            if not ioc:
                ioc = self.indicators.check_domain(result.get("history_url", ""))

            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)

    def run(self) -> None:
        self._find_ios_database(backup_ids=FIREFOX_HISTORY_BACKUP_IDS,
                                root_paths=FIREFOX_HISTORY_ROOT_PATHS)
        self.log.info("Found Firefox favicon database at path: %s", self.file_path)

        conn = sqlite3.connect(self.file_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT
                favicons.id,
                favicons.url,
                favicons.width,
                favicons.height,
                favicons.type,
                favicons.date,
                history.id,
                history.url
            FROM favicons
            INNER JOIN favicon_sites ON favicon_sites.faviconID = favicons.id
            INNER JOIN history ON favicon_sites.siteID = history.id;
        """)

        for item in cur:
            self.results.append({
                "id": item[0],
                "url": item[1],
                "width": item[2],
                "height": item[3],
                "type": item[4],
                "isodate": convert_timestamp_to_iso(datetime.utcfromtimestamp(item[5])),
                "history_id": item[6],
                "history_url": item[7]
            })

        cur.close()
        conn.close()

        self.log.info("Extracted a total of %d history items", len(self.results))
