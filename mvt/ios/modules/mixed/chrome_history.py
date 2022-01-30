# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import sqlite3

from mvt.common.utils import (convert_chrometime_to_unix,
                              convert_timestamp_to_iso)

from ..base import IOSExtraction

CHROME_HISTORY_BACKUP_IDS = [
    "faf971ce92c3ac508c018dce1bef2a8b8e9838f1",
]
# TODO: Confirm Chrome database path.
CHROME_HISTORY_ROOT_PATHS = [
    "private/var/mobile/Containers/Data/Application/*/Library/Application Support/Google/Chrome/Default/History",
]


class ChromeHistory(IOSExtraction):
    """This module extracts all Chome visits."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record):
        return {
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": "visit",
            "data": f"{record['id']} - {record['url']} (visit ID: {record['visit_id']}, redirect source: {record['redirect_source']})"
        }

    def check_indicators(self):
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_domain(result["url"])
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)

    def run(self):
        self._find_ios_database(backup_ids=CHROME_HISTORY_BACKUP_IDS,
                                root_paths=CHROME_HISTORY_ROOT_PATHS)
        self.log.info("Found Chrome history database at path: %s", self.file_path)

        conn = sqlite3.connect(self.file_path)
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

        self.log.info("Extracted a total of %d history items", len(self.results))
