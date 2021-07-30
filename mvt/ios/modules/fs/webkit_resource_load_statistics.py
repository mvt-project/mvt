# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 MVT Project Developers.
# See the file 'LICENSE' for usage and copying permissions, or find a copy at
#   https://github.com/mvt-project/mvt/blob/main/LICENSE

import datetime
import os
import sqlite3

from mvt.common.utils import convert_mactime_to_unix, convert_timestamp_to_iso

from .base import IOSExtraction

WEBKIT_RESOURCELOADSTATICS_BACKUP_RELPATH = "Library/WebKit/WebsiteData/ResourceLoadStatistics/observations.db"
WEBKIT_RESOURCELOADSTATICS_ROOT_PATHS = [
    "private/var/mobile/Containers/Data/Application/*/Library/WebKit/WebsiteData/ResourceLoadStatistics/observations.db",
    "private/var/mobile/Containers/Data/Application/*/SystemData/com.apple.SafariViewService/Library/WebKit/WebsiteData/observations.db",
]

class WebkitResourceLoadStatistics(IOSExtraction):
    """This module extracts records from WebKit ResourceLoadStatistics observations.db.
    """
    # TODO: Add serialize().

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def check_indicators(self):
        if not self.indicators:
            return

        self.detected = {}
        for key, items in self.results.items():
            for item in items:
                if self.indicators.check_domain(item["registrable_domain"]):
                    if key not in self.detected:
                        self.detected[key] = [item,]
                    else:
                        self.detected[key].append(item)

    def _process_observations_db(self, db_path, key):
        self.log.info("Found WebKit ResourceLoadStatistics observations.db file at path %s", db_path)

        if self._is_database_malformed(db_path):
            self._recover_database(db_path)

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        try:
            cur.execute("SELECT * from ObservedDomains;")
        except sqlite3.OperationalError:
            return

        if not key in self.results:
            self.results[key] = []

        for row in cur:
            self.results[key].append(dict(
                domain_id=row[0],
                registrable_domain=row[1],
                last_seen=row[2],
                had_user_interaction=bool(row[3]),
                # TODO: Fix isodate.
                last_seen_isodate=convert_timestamp_to_iso(datetime.datetime.utcfromtimestamp(int(row[2]))),
            ))

        if len(self.results[key]) > 0:
            self.log.info("Extracted a total of %d records from %s", len(self.results[key]), db_path)

    def run(self):
        self.results = {}

        if self.is_backup:
            manifest_db_path = os.path.join(self.base_folder, "Manifest.db")
            if not os.path.exists(manifest_db_path):
                self.log.info("Unable to search for WebKit observations.db files in backup because of missing Manifest.db")
                return

            try:
                conn = sqlite3.connect(manifest_db_path)
                cur = conn.cursor()
                cur.execute("SELECT fileID, domain FROM Files WHERE relativePath = ?;", (WEBKIT_RESOURCELOADSTATICS_BACKUP_RELPATH,))
            except Exception as e:
                self.log.error("Unable to search for WebKit observations.db files in backup because of failed query to Manifest.db: %s", e)

            for row in cur:
                file_id = row[0]
                domain = row[1]
                db_path = os.path.join(self.base_folder, file_id[0:2], file_id)
                if os.path.exists(db_path):
                    self._process_observations_db(db_path=db_path, key=f"{domain}/{WEBKIT_RESOURCELOADSTATICS_BACKUP_RELPATH}")
        elif self.is_fs_dump:
            for db_path in self._find_paths(WEBKIT_RESOURCELOADSTATICS_ROOT_PATHS):
                self._process_observations_db(db_path=db_path, key=os.path.relpath(db_path, self.base_folder))
