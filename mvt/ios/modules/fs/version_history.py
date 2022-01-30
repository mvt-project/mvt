# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import datetime
import json

from mvt.common.utils import convert_timestamp_to_iso

from ..base import IOSExtraction

IOS_ANALYTICS_JOURNAL_PATHS = [
    "private/var/db/analyticsd/Analytics-Journal-*.ips",
]


class IOSVersionHistory(IOSExtraction):
    """This module extracts iOS update history from Analytics Journal log files."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record):
        return {
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": "ios_version",
            "data": f"Recorded iOS version {record['os_version']}",
        }

    def run(self):
        for found_path in self._get_fs_files_from_patterns(IOS_ANALYTICS_JOURNAL_PATHS):
            with open(found_path, "r", encoding="utf-8") as analytics_log:
                log_line = json.loads(analytics_log.readline().strip())

                timestamp = datetime.datetime.strptime(log_line["timestamp"],
                                                       "%Y-%m-%d %H:%M:%S.%f %z")
                timestamp_utc = timestamp.astimezone(datetime.timezone.utc)
                self.results.append({
                    "isodate": convert_timestamp_to_iso(timestamp_utc),
                    "os_version": log_line["os_version"],
                })

        self.results = sorted(self.results, key=lambda entry: entry["isodate"])
