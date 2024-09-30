# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
import sqlite3
from typing import Optional, Union

from mvt.common.utils import convert_unix_to_iso

from ..base import IOSExtraction

WEBKIT_RESOURCELOADSTATICS_BACKUP_RELPATH = "Library/WebKit/WebsiteData/ResourceLoadStatistics/observations.db"  # pylint: disable=line-too-long
WEBKIT_RESOURCELOADSTATICS_ROOT_PATHS = [
    "private/var/mobile/Containers/Data/Application/*/Library/WebKit/WebsiteData/ResourceLoadStatistics/observations.db",  # pylint: disable=line-too-long
    "private/var/mobile/Containers/Data/Application/*/SystemData/com.apple.SafariViewService/Library/WebKit/WebsiteData/observations.db",  # pylint: disable=line-too-long
]


class WebkitResourceLoadStatistics(IOSExtraction):
    """This module extracts records from WebKit ResourceLoadStatistics
    observations.db."""

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

        self.results = [] if not results else results

    def serialize(self, record: dict) -> Union[dict, list]:
        msg = f"Webkit resource loaded from {record['registrable_domain']}"
        if record["domain"] != "":
            msg += f" by app in domain {record['domain']}"
        return {
            "timestamp": record["last_seen_isodate"],
            "module": self.__class__.__name__,
            "event": "visit",
            "data": msg,
        }

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        self.detected = []
        for result in self.results:
            ioc = self.indicators.check_domain(result["registrable_domain"])
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)

    def _process_observations_db(self, db_path: str, domain: str, path: str) -> None:
        self.log.info(
            "Found WebKit ResourceLoadStatistics observations.db file at path %s",
            db_path,
        )

        self._recover_sqlite_db_if_needed(db_path)

        conn = self._open_sqlite_db(db_path)
        cur = conn.cursor()

        try:
            # FIXME: table contains extra fields with timestamp here
            cur.execute(
                """
                SELECT
                    domainID,
                    registrableDomain,
                    lastSeen,
                    hadUserInteraction
                from ObservedDomains;
            """
            )
        except sqlite3.OperationalError:
            return

        for row in cur:
            self.results.append(
                {
                    "domain_id": row[0],
                    "registrable_domain": row[1],
                    "last_seen": row[2],
                    "had_user_interaction": bool(row[3]),
                    "last_seen_isodate": convert_unix_to_iso(row[2]),
                    "domain": domain,
                    "path": path,
                }
            )

        if len(self.results) > 0:
            self.log.info(
                "Extracted a total of %d records from %s", len(self.results), db_path
            )

    def run(self) -> None:
        if self.is_backup:
            try:
                for backup_file in self._get_backup_files_from_manifest(
                    relative_path=WEBKIT_RESOURCELOADSTATICS_BACKUP_RELPATH
                ):
                    db_path = self._get_backup_file_from_id(backup_file["file_id"])

                    if db_path:
                        self._process_observations_db(
                            db_path=db_path,
                            domain=backup_file["domain"],
                            path=WEBKIT_RESOURCELOADSTATICS_BACKUP_RELPATH,
                        )
            except Exception as exc:
                self.log.info("Unable to find WebKit observations.db: %s", exc)
        elif self.is_fs_dump:
            for db_path in self._get_fs_files_from_patterns(
                WEBKIT_RESOURCELOADSTATICS_ROOT_PATHS
            ):
                db_rel_path = os.path.relpath(db_path, self.target_path)
                self._process_observations_db(
                    db_path=db_path, domain="", path=db_rel_path
                )
