# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import plistlib
import sqlite3

from mvt.common.utils import convert_mactime_to_unix, convert_timestamp_to_iso

from ..base import IOSExtraction

ANALYTICS_DB_PATH = [
    "private/var/Keychains/Analytics/*.db",
]


class Analytics(IOSExtraction):
    """This module extracts information from the private/var/Keychains/Analytics/*.db files."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record):
        return {
            "timestamp": record["timestamp"],
            "module": self.__class__.__name__,
            "event": record["artifact"],
            "data": f"{record}",
        }

    def check_indicators(self):
        if not self.indicators:
            return

        for result in self.results:
            for ioc in self.indicators.ioc_processes:
                for key in result.keys():
                    if ioc == result[key]:
                        self.log.warning("Found mention of a malicious process \"%s\" in %s file at %s",
                                         ioc, result["artifact"], result["timestamp"])
                        self.detected.append(result)
                        break
            for ioc in self.indicators.ioc_domains:
                for key in result.keys():
                    if ioc in str(result[key]):
                        self.log.warning("Found mention of a malicious domain \"%s\" in %s file at %s",
                                         ioc, result["artifact"], result["timestamp"])
                        self.detected.append(result)
                        break

    def _extract_analytics_data(self):
        artifact = self.file_path.split("/")[-1]

        conn = sqlite3.connect(self.file_path)
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT
                    timestamp,
                    data
                FROM hard_failures
                UNION
                SELECT
                    timestamp,
                    data
                FROM soft_failures
                UNION
                SELECT
                    timestamp,
                    data
                FROM all_events;
            """)
        except sqlite3.OperationalError:
            cur.execute("""
                SELECT
                    timestamp,
                    data
                FROM hard_failures
                UNION
                SELECT
                    timestamp,
                    data
                FROM soft_failures;
            """)

        for row in cur:
            if row[0] and row[1]:
                timestamp = convert_timestamp_to_iso(convert_mactime_to_unix(row[0], False))
                data = plistlib.loads(row[1])
                data["timestamp"] = timestamp
            elif row[0]:
                timestamp = convert_timestamp_to_iso(convert_mactime_to_unix(row[0], False))
                data = {}
                data["timestamp"] = timestamp
            elif row[1]:
                timestamp = ""
                data = plistlib.loads(row[1])
                data["timestamp"] = timestamp
            data["artifact"] = artifact

            self.results.append(data)

        self.results = sorted(self.results, key=lambda entry: entry["timestamp"])

        cur.close()
        conn.close()

        self.log.info("Extracted information on %d analytics data from %s", len(self.results), artifact)

    def run(self):
        for file_path in self._get_fs_files_from_patterns(ANALYTICS_DB_PATH):
            self.file_path = file_path
            self.log.info("Found Analytics database file at path: %s", file_path)
            self._extract_analytics_data()
