# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
from typing import Optional

from .base import AndroidExtraction


class Logcat(AndroidExtraction):
    """This module extracts details on installed packages."""

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

    def run(self) -> None:
        self._adb_connect()

        # Get the current logcat.
        output = self._adb_command('logcat -d -b all "*:V"')
        # Get the locat prior to last reboot.
        last_output = self._adb_command('logcat -L -b all "*:V"')

        if self.results_path:
            logcat_path = os.path.join(self.results_path, "logcat.txt")
            with open(logcat_path, "w", encoding="utf-8") as handle:
                handle.write(output)

            self.log.info("Current logcat logs stored at %s", logcat_path)

            logcat_last_path = os.path.join(self.results_path, "logcat_last.txt")
            with open(logcat_last_path, "w", encoding="utf-8") as handle:
                handle.write(last_output)

            self.log.info(
                "Logcat logs prior to last reboot stored at %s", logcat_last_path
            )

        self._adb_disconnect()
