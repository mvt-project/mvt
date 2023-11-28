# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import io
import logging
import os
import plistlib
import sqlite3
from typing import Optional, Union

from mvt.common.utils import convert_mactime_to_iso, keys_bytes_to_string

from ..base import IOSExtraction

SAFARI_BROWSER_STATE_BACKUP_RELPATH = "Library/Safari/BrowserState.db"
SAFARI_BROWSER_STATE_ROOT_PATHS = [
    "private/var/mobile/Library/Safari/BrowserState.db",
    "private/var/mobile/Containers/Data/Application/*/Library/Safari/BrowserState.db",
]


class SafariBrowserState(IOSExtraction):
    """This module extracts all Safari browser state records."""

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

        self._session_history_count = 0

    def serialize(self, record: dict) -> Union[dict, list]:
        return {
            "timestamp": record["last_viewed_timestamp"],
            "module": self.__class__.__name__,
            "event": "tab",
            "data": f"{record['tab_title']} - {record['tab_url']}",
        }

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            if "tab_url" in result:
                ioc = self.indicators.check_domain(result["tab_url"])
                if ioc:
                    result["matched_indicator"] = ioc
                    self.detected.append(result)
                    continue

            if "session_data" not in result:
                continue

            for session_entry in result["session_data"]:
                if "entry_url" in session_entry:
                    ioc = self.indicators.check_domain(session_entry["entry_url"])
                    if ioc:
                        result["matched_indicator"] = ioc
                        self.detected.append(result)

    def _process_browser_state_db(self, db_path):
        self._recover_sqlite_db_if_needed(db_path)
        conn = self._open_sqlite_db(db_path)

        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT
                    tabs.title,
                    tabs.url,
                    tabs.user_visible_url,
                    tabs.last_viewed_time,
                    tab_sessions.session_data
                FROM tabs
                JOIN tab_sessions ON tabs.uuid = tab_sessions.tab_uuid
                ORDER BY tabs.last_viewed_time;
            """
            )
        except sqlite3.OperationalError:
            # Old version iOS <12 likely
            cur.execute(
                """
                SELECT
                    title, url, user_visible_url, last_viewed_time, session_data
                FROM tabs
                ORDER BY last_viewed_time;
            """
            )

        for row in cur:
            session_entries = []

            if row[4]:
                # Skip a 4 byte header before the plist content.
                session_plist = row[4][4:]
                session_data = {}
                try:
                    session_data = plistlib.load(io.BytesIO(session_plist))
                    session_data = keys_bytes_to_string(session_data)
                except plistlib.InvalidFileException:
                    pass

                if "SessionHistoryEntries" in session_data.get("SessionHistory", {}):
                    for session_entry in session_data["SessionHistory"].get(
                        "SessionHistoryEntries"
                    ):
                        self._session_history_count += 1

                        data_length = 0
                        if "SessionHistoryEntryData" in session_entry:
                            data_length = len(
                                session_entry.get("SessionHistoryEntryData")
                            )

                        session_entries.append(
                            {
                                "entry_title": session_entry.get(
                                    "SessionHistoryEntryOriginalURL"
                                ),
                                "entry_url": session_entry.get(
                                    "SessionHistoryEntryURL"
                                ),
                                "data_length": data_length,
                            }
                        )

            self.results.append(
                {
                    "tab_title": row[0],
                    "tab_url": row[1],
                    "tab_visible_url": row[2],
                    "last_viewed_timestamp": convert_mactime_to_iso(row[3]),
                    "session_data": session_entries,
                    "safari_browser_state_db": os.path.relpath(
                        db_path, self.target_path
                    ),
                }
            )

    def run(self) -> None:
        if self.is_backup:
            for backup_file in self._get_backup_files_from_manifest(
                relative_path=SAFARI_BROWSER_STATE_BACKUP_RELPATH
            ):
                browserstate_path = self._get_backup_file_from_id(
                    backup_file["file_id"]
                )

                if not browserstate_path:
                    continue

                self.log.info(
                    "Found Safari browser state database at path: %s", browserstate_path
                )
                self._process_browser_state_db(browserstate_path)
        elif self.is_fs_dump:
            for browserstate_path in self._get_fs_files_from_patterns(
                SAFARI_BROWSER_STATE_ROOT_PATHS
            ):
                self.log.info(
                    "Found Safari browser state database at path: %s", browserstate_path
                )
                self._process_browser_state_db(browserstate_path)

        self.log.info(
            "Extracted a total of %d tab records and %d session history entries",
            len(self.results),
            self._session_history_count,
        )
