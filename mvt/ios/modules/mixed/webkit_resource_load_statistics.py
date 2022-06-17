# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import datetime
import logging
import os
import sqlite3

from mvt.common.utils import convert_timestamp_to_iso

from ..base import IOSExtraction

WEBKIT_RESOURCELOADSTATICS_BACKUP_RELPATH = "Library/WebKit/WebsiteData/ResourceLoadStatistics/observations.db"
WEBKIT_RESOURCELOADSTATICS_ROOT_PATHS = [
    "private/var/mobile/Containers/Data/Application/*/Library/WebKit/WebsiteData/ResourceLoadStatistics/observations.db",
    "private/var/mobile/Containers/Data/Application/*/SystemData/com.apple.SafariViewService/Library/WebKit/WebsiteData/observations.db",
]


class WebkitResourceLoadStatistics(IOSExtraction):
    """This module extracts records from WebKit ResourceLoadStatistics observations.db."""
    # TODO: Add serialize().

    def __init__(self, file_path: str = None, target_path: str = None,
                 results_path: str = None, fast_mode: bool = False,
                 log: logging.Logger = None, results: list = []) -> None:
        super().__init__(file_path=file_path, target_path=target_path,
                         results_path=results_path, fast_mode=fast_mode,
                         log=log, results=results)

        self.results = {} if not results else results

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        self.detected = {}
        for key, items in self.results.items():
            for item in items:
                ioc = self.indicators.check_domain(item["registrable_domain"])
                if ioc:
                    item["matched_indicator"] = ioc
                    if key not in self.detected:
                        self.detected[key] = [item, ]
                    else:
                        self.detected[key].append(item)

    def _process_observations_db(self, db_path, key):
        self.log.info("Found WebKit ResourceLoadStatistics observations.db file at path %s", db_path)

        self._recover_sqlite_db_if_needed(db_path)

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        try:
            cur.execute("SELECT * from ObservedDomains;")
        except sqlite3.OperationalError:
            return

        if key not in self.results:
            self.results[key] = []

        for row in cur:
            self.results[key].append({
                "domain_id": row[0],
                "registrable_domain": row[1],
                "last_seen": row[2],
                "had_user_interaction": bool(row[3]),
                "last_seen_isodate": convert_timestamp_to_iso(datetime.datetime.utcfromtimestamp(int(row[2]))),
            })

        if len(self.results[key]) > 0:
            self.log.info("Extracted a total of %d records from %s", len(self.results[key]), db_path)

    def run(self) -> None:
        if self.is_backup:
            try:
                for backup_file in self._get_backup_files_from_manifest(relative_path=WEBKIT_RESOURCELOADSTATICS_BACKUP_RELPATH):
                    db_path = self._get_backup_file_from_id(backup_file["file_id"])
                    key = f"{backup_file['domain']}/{WEBKIT_RESOURCELOADSTATICS_BACKUP_RELPATH}"
                    if db_path:
                        self._process_observations_db(db_path=db_path, key=key)
            except Exception as e:
                self.log.info("Unable to search for WebKit observations.db: %s", e)
        elif self.is_fs_dump:
            for db_path in self._get_fs_files_from_patterns(WEBKIT_RESOURCELOADSTATICS_ROOT_PATHS):
                self._process_observations_db(db_path=db_path, key=os.path.relpath(db_path, self.target_path))
