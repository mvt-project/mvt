# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import plistlib
from typing import Optional

from ..base import IOSExtraction

GLOBAL_PREFERENCES_BACKUP_IDS = ["0dc926a1810f7aee4e8f38793ed788701f93bf9d"]
GLOBAL_PREFERENCES_ROOT_PATHS = [
    "private/var/mobile/Library/Preferences/.GlobalPreferences.plist",
]


class GlobalPreferences(IOSExtraction):
    """This module extracts Global Preferences to check if Lockdown mode is enabled."""

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

    def check_indicators(self) -> None:
        for entry in self.results:
            if entry["entry"] == "LDMGlobalEnabled":
                if entry["value"]:
                    self.log.warning("Lockdown mode enabled")
                else:
                    self.log.warning("Lockdown mode disabled")

    def process_file(self, file_path: str) -> None:
        with open(file_path, "rb") as handle:
            data = plistlib.load(handle)

        for entry in data:
            self.results.append({"entry": entry, "value": data[entry]})

    def run(self) -> None:
        self._find_ios_database(
            backup_ids=GLOBAL_PREFERENCES_BACKUP_IDS,
            root_paths=GLOBAL_PREFERENCES_ROOT_PATHS,
        )
        self.log.info("Found Global Preference database at path: %s", self.file_path)

        self.process_file(self.file_path)

        self.log.info("Extracted a total of %d Global Preferences", len(self.results))
