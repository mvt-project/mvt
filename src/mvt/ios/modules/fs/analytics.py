# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import copy
import logging
import plistlib
import sqlite3
from typing import Optional, Union

from mvt.common.utils import convert_mactime_to_iso

from ..base import IOSExtraction

ANALYTICS_DB_PATH = [
    "private/var/Keychains/Analytics/*.db",
]


class Analytics(IOSExtraction):
    """This module extracts information from the
    private/var/Keychains/Analytics/*.db files."""

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
            "event": record["artifact"],
            "data": f"{record}",
        }

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            for value in result.values():
                if not isinstance(value, str):
                    continue

                ioc = self.indicators.check_process(value)
                if ioc:
                    self.log.warning(
                        'Found mention of a malicious process "%s" in %s file at %s',
                        value,
                        result["artifact"],
                        result["isodate"],
                    )
                    new_result = copy.copy(result)
                    new_result["matched_indicator"] = ioc
                    self.detected.append(new_result)
                    continue

                ioc = self.indicators.check_domain(value)
                if ioc:
                    self.log.warning(
                        'Found mention of a malicious domain "%s" in %s file at %s',
                        value,
                        result["artifact"],
                        result["isodate"],
                    )
                    new_result = copy.copy(result)
                    new_result["matched_indicator"] = ioc
                    self.detected.append(new_result)

    def _extract_analytics_data(self):
        artifact = self.file_path.split("/")[-1]

        conn = self._open_sqlite_db(self.file_path)
        cur = conn.cursor()

        try:
            cur.execute(
                """
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
            """
            )
        except sqlite3.OperationalError:
            cur.execute(
                """
                SELECT
                    timestamp,
                    data
                FROM hard_failures
                UNION
                SELECT
                    timestamp,
                    data
                FROM soft_failures;
            """
            )

        for row in cur:
            if row[0] and row[1]:
                isodate = convert_mactime_to_iso(row[0], False)
                data = plistlib.loads(row[1])
                data["isodate"] = isodate
            elif row[0]:
                isodate = convert_mactime_to_iso(row[0], False)
                data = {}
                data["isodate"] = isodate
            elif row[1]:
                isodate = ""
                data = plistlib.loads(row[1])
                data["isodate"] = isodate

            data["artifact"] = artifact

            self.results.append(data)

        cur.close()
        conn.close()

    def process_analytics_dbs(self):
        for file_path in self._get_fs_files_from_patterns(ANALYTICS_DB_PATH):
            self.file_path = file_path
            self.log.info("Found Analytics database file at path: %s", file_path)
            self._extract_analytics_data()

    def run(self) -> None:
        self.process_analytics_dbs()

        self.log.info(
            "Extracted %d records from analytics databases", len(self.results)
        )

        self.results = sorted(self.results, key=lambda entry: entry["isodate"])
