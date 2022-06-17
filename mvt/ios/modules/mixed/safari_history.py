# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
import sqlite3

from mvt.common.url import URL
from mvt.common.utils import convert_mactime_to_unix, convert_timestamp_to_iso

from ..base import IOSExtraction

SAFARI_HISTORY_BACKUP_RELPATH = "Library/Safari/History.db"
SAFARI_HISTORY_ROOT_PATHS = [
    "private/var/mobile/Library/Safari/History.db",
    "private/var/mobile/Containers/Data/Application/*/Library/Safari/History.db",
]


class SafariHistory(IOSExtraction):
    """This module extracts all Safari visits and tries to detect potential
    network injection attacks.


    """

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
            "event": "safari_history",
            "data": f"Safari visit to {record['url']} (ID: {record['id']}, Visit ID: {record['visit_id']})",
        }

    def _find_injections(self):
        for result in self.results:
            # We presume injections only happen on HTTP visits.
            if not result["url"].lower().startswith("http://"):
                continue

            # If there is no destination, no redirect happened.
            if not result["redirect_destination"]:
                continue

            origin_domain = URL(result["url"]).domain

            # We loop again through visits in order to find redirect record.
            for redirect in self.results:
                if redirect["visit_id"] != result["redirect_destination"]:
                    continue

                redirect_domain = URL(redirect["url"]).domain
                # If the redirect destination is the same domain as the origin,
                # it's most likely an HTTPS upgrade.
                if origin_domain == redirect_domain:
                    continue

                self.log.info("Found HTTP redirect to different domain: \"%s\" -> \"%s\"",
                              origin_domain, redirect_domain)

                redirect_time = convert_mactime_to_unix(redirect["timestamp"])
                origin_time = convert_mactime_to_unix(result["timestamp"])
                elapsed_time = redirect_time - origin_time
                elapsed_ms = elapsed_time.microseconds / 1000

                if elapsed_time.seconds == 0:
                    self.log.warning("Redirect took less than a second! (%d milliseconds)", elapsed_ms)

    def check_indicators(self) -> None:
        self._find_injections()

        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_domain(result["url"])
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)

    def _process_history_db(self, history_path):
        self._recover_sqlite_db_if_needed(history_path)
        conn = sqlite3.connect(history_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT
                history_items.id,
                history_items.url,
                history_visits.id,
                history_visits.visit_time,
                history_visits.redirect_source,
                history_visits.redirect_destination
            FROM history_items
            JOIN history_visits ON history_visits.history_item = history_items.id
            ORDER BY history_visits.visit_time;
        """)

        for row in cur:
            self.results.append({
                "id": row[0],
                "url": row[1],
                "visit_id": row[2],
                "timestamp": row[3],
                "isodate": convert_timestamp_to_iso(convert_mactime_to_unix(row[3])),
                "redirect_source": row[4],
                "redirect_destination": row[5],
                "safari_history_db": os.path.relpath(history_path, self.target_path),
            })

        cur.close()
        conn.close()

    def run(self) -> None:
        if self.is_backup:
            for history_file in self._get_backup_files_from_manifest(relative_path=SAFARI_HISTORY_BACKUP_RELPATH):
                history_path = self._get_backup_file_from_id(history_file["file_id"])
                if not history_path:
                    continue

                self.log.info("Found Safari history database at path: %s", history_path)
                self._process_history_db(history_path)
        elif self.is_fs_dump:
            for history_path in self._get_fs_files_from_patterns(SAFARI_HISTORY_ROOT_PATHS):
                self.log.info("Found Safari history database at path: %s", history_path)
                self._process_history_db(history_path)

        self.log.info("Extracted a total of %d history records", len(self.results))
