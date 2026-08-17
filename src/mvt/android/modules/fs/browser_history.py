# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import sqlite3
from pathlib import Path
from typing import Optional

from mvt.android.artifacts.browser_history import (
    BrowserHistoryArtifact,
    open_browser_history_database,
)
from mvt.common.module import MVTModule
from mvt.common.module_types import ModuleResults


# These locations are deliberately limited to paths backed by public parser
# fixtures or the historical MVT implementation.
BROWSER_HISTORY_PATHS = {
    "data/data/com.android.chrome/app_chrome/Default/History": (
        "Chrome",
        "com.android.chrome",
        "Default",
    ),
    "data/data/com.brave.browser/app_chrome/Default/History": (
        "Brave",
        "com.brave.browser",
        "Default",
    ),
    "data/data/com.microsoft.emmx/app_chrome/Default/History": (
        "Microsoft Edge",
        "com.microsoft.emmx",
        "Default",
    ),
    "data/data/com.sec.android.app.sbrowser/app_sbrowser/Default/History": (
        "Samsung Internet",
        "com.sec.android.app.sbrowser",
        "Default",
    ),
}


class BrowserHistory(BrowserHistoryArtifact, MVTModule):
    """Extract supported Chromium History databases from a filesystem dump."""

    supported_commands = (("android", "check-fs"),)

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        module_options: Optional[dict] = None,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[ModuleResults] = None,
    ) -> None:
        super().__init__(
            file_path=file_path,
            target_path=target_path,
            results_path=results_path,
            module_options=module_options,
            log=log,
            results=results,
        )

    def _database_paths(self) -> list[tuple[Path, str, str, str]]:
        if not self.target_path:
            return []
        target = Path(self.target_path)
        if target.is_file():
            normalized_target = target.resolve().as_posix()
            for relative_path, identity in BROWSER_HISTORY_PATHS.items():
                if normalized_target.endswith(f"/{relative_path}"):
                    return [(target, *identity)]
            return [(target, "Chromium", "unknown", "unknown")]

        databases = []
        for relative_path, identity in BROWSER_HISTORY_PATHS.items():
            database_path = target / relative_path
            if database_path.is_file():
                databases.append((database_path, *identity))
        return databases

    def run(self) -> None:
        for database_path, browser, package, profile in self._database_paths():
            try:
                connection = open_browser_history_database(database_path)
                try:
                    self._parse_browser_history(
                        connection,
                        browser=browser,
                        package=package,
                        profile=profile,
                        source_path=str(database_path),
                    )
                finally:
                    connection.close()
            except (
                OSError,
                OverflowError,
                sqlite3.Error,
                TypeError,
                ValueError,
            ) as exc:
                self.log.error(
                    "Unable to parse browser history database %s: %s",
                    database_path,
                    exc,
                )

        self.log.info(
            "Extracted a total of %d browser history items", len(self.results)
        )
