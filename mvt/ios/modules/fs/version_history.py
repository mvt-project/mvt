# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import datetime
import json
import logging
from typing import Optional, Union

from mvt.common.utils import convert_datetime_to_iso

from ..base import IOSExtraction

IOS_ANALYTICS_JOURNAL_PATHS = [
    "private/var/db/analyticsd/Analytics-Journal-*.ips",
]


class IOSVersionHistory(IOSExtraction):
    """This module extracts iOS update history from Analytics Journal log files."""

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
        return {
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": "ios_version",
            "data": f"Recorded iOS version {record['os_version']}",
        }

    def run(self) -> None:
        for found_path in self._get_fs_files_from_patterns(IOS_ANALYTICS_JOURNAL_PATHS):
            with open(found_path, "r", encoding="utf-8") as analytics_log:
                log_line = json.loads(analytics_log.readline().strip())

                timestamp = datetime.datetime.strptime(
                    log_line["timestamp"], "%Y-%m-%d %H:%M:%S.%f %z"
                )
                timestamp_utc = timestamp.astimezone(datetime.timezone.utc)
                self.results.append(
                    {
                        "isodate": convert_datetime_to_iso(timestamp_utc),
                        "os_version": log_line["os_version"],
                    }
                )

        self.results = sorted(self.results, key=lambda entry: entry["isodate"])
