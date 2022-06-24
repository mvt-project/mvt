# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
import sqlite3

from mvt.common.utils import (convert_chrometime_to_unix,
                              convert_timestamp_to_iso)

from .base import AndroidExtraction

log = logging.getLogger(__name__)

CHROME_HISTORY_PATH = "data/data/com.android.chrome/app_chrome/Default/History"


class ChromeHistory(AndroidExtraction):
    """This module extracts records from Android's Chrome browsing history."""

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
            "event": "visit",
            "data": f"{record['id']} - {record['url']} (visit ID: {record['visit_id']}, redirect source: {record['redirect_source']})"
        }

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            if self.indicators.check_domain(result["url"]):
                self.detected.append(result)

    def _parse_db(self, db_path: str) -> None:
        """Parse a Chrome History database file.

        :param db_path: Path to the History database to process.

        """
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT
                urls.id,
                urls.url,
                visits.id,
                visits.visit_time,
                visits.from_visit
            FROM urls
            JOIN visits ON visits.url = urls.id
            ORDER BY visits.visit_time;
        """)

        for item in cur:
            self.results.append({
                "id": item[0],
                "url": item[1],
                "visit_id": item[2],
                "timestamp": item[3],
                "isodate": convert_timestamp_to_iso(convert_chrometime_to_unix(item[3])),
                "redirect_source": item[4],
            })

        cur.close()
        conn.close()

        log.info("Extracted a total of %d history items", len(self.results))

    def run(self) -> None:
        try:
            self._adb_process_file(os.path.join("/", CHROME_HISTORY_PATH),
                                   self._parse_db)
        except Exception as e:
            self.log.error(e)
