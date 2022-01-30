# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import sqlite3

from mvt.common.utils import (convert_chrometime_to_unix,
                              convert_timestamp_to_iso)

from ..base import IOSExtraction

CHROME_FAVICON_BACKUP_IDS = [
    "55680ab883d0fdcffd94f959b1632e5fbbb18c5b"
]

# TODO: Confirm Chrome database path.
CHROME_FAVICON_ROOT_PATHS = [
    "private/var/mobile/Containers/Data/Application/*/Library/Application Support/Google/Chrome/Default/Favicons",
]


class ChromeFavicon(IOSExtraction):
    """This module extracts all Chrome favicon records."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record):
        return {
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": "new_favicon",
            "data": f"{record['icon_url']} from {record['url']}"
        }

    def check_indicators(self):
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_domain(result["url"])
            if not ioc:
                ioc = self.indicators.check_domain(result["icon_url"])

            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)

    def run(self):
        self._find_ios_database(backup_ids=CHROME_FAVICON_BACKUP_IDS,
                                root_paths=CHROME_FAVICON_ROOT_PATHS)
        self.log.info("Found Chrome favicon cache database at path: %s", self.file_path)

        conn = sqlite3.connect(self.file_path)

        # Fetch icon cache
        cur = conn.cursor()
        cur.execute("""
            SELECT
                icon_mapping.page_url,
                favicons.url,
                favicon_bitmaps.last_updated,
                favicon_bitmaps.last_requested
            FROM icon_mapping
            JOIN favicon_bitmaps ON icon_mapping.icon_id = favicon_bitmaps.icon_id
            JOIN favicons ON icon_mapping.icon_id = favicons.id
            ORDER BY icon_mapping.id;
        """)

        records = []
        for row in cur:
            last_timestamp = int(row[2]) or int(row[3])
            records.append({
                "url": row[0],
                "icon_url": row[1],
                "timestamp": last_timestamp,
                "isodate": convert_timestamp_to_iso(convert_chrometime_to_unix(last_timestamp)),
            })

        cur.close()
        conn.close()

        self.log.info("Extracted a total of %d favicon records", len(records))
        self.results = sorted(records, key=lambda row: row["isodate"])
