# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 MVT Project Developers.
# See the file 'LICENSE' for usage and copying permissions, or find a copy at
#   https://github.com/mvt-project/mvt/blob/main/LICENSE

import sqlite3

from mvt.common.utils import convert_mactime_to_unix, convert_timestamp_to_iso

from .base import IOSExtraction

SAFARI_FAVICON_ROOT_PATHS = [
    "private/var/mobile/Library/Image Cache/Favicons/Favicons.db",
    "private/var/mobile/Containers/Data/Application/*/Library/Image Cache/Favicons/Favicons.db",
]

class SafariFavicon(IOSExtraction):
    """This module extracts all Safari favicon records."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record):
        return {
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": "safari_favicon",
            "data": f"Safari favicon from {record['url']} with icon URL {record['icon_url']} ({record['type']})",
        }

    def check_indicators(self):
        if not self.indicators:
            return

        for result in self.results:
            if self.indicators.check_domain(result["url"]) or self.indicators.check_domain(result["icon_url"]):
                self.detected.append(result)

    def run(self):
        self._find_ios_database(root_paths=SAFARI_FAVICON_ROOT_PATHS)
        self.log.info("Found Safari favicon cache database at path: %s", self.file_path)

        conn = sqlite3.connect(self.file_path)

        # Fetch valid icon cache.
        cur = conn.cursor()
        cur.execute("""SELECT
                page_url.url,
                icon_info.url,
                icon_info.timestamp
            FROM page_url
            JOIN icon_info ON page_url.uuid = icon_info.uuid
            ORDER BY icon_info.timestamp;""")

        items = []
        for item in cur:
            items.append(dict(
                url=item[0],
                icon_url=item[1],
                timestamp=item[2],
                isodate=convert_timestamp_to_iso(convert_mactime_to_unix(item[2])),
                type="valid",
            ))

        # Fetch icons from the rejected icons table.
        cur.execute("""SELECT
                page_url,
                icon_url,
                timestamp
            FROM rejected_resources ORDER BY timestamp;""")

        for item in cur:
            items.append(dict(
                url=item[0],
                icon_url=item[1],
                timestamp=item[2],
                isodate=convert_timestamp_to_iso(convert_mactime_to_unix(item[2])),
                type="rejected",
            ))

        cur.close()
        conn.close()

        self.log.info("Extracted a total of %d favicon records", len(items))
        self.results = sorted(items, key=lambda item: item["isodate"])
