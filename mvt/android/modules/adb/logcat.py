# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os

from .base import AndroidExtraction

log = logging.getLogger(__name__)


class Logcat(AndroidExtraction):
    """This module extracts details on installed packages."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 serial=None, fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def run(self):
        self._adb_connect()

        # Get the current logcat.
        output = self._adb_command("logcat -d")
        # Get the locat prior to last reboot.
        last_output = self._adb_command("logcat -L")

        if self.output_folder:
            logcat_path = os.path.join(self.output_folder,
                                       "logcat.txt")
            with open(logcat_path, "w", encoding="utf-8") as handle:
                handle.write(output)

            log.info("Current logcat logs stored at %s",
                     logcat_path)

            logcat_last_path = os.path.join(self.output_folder,
                                            "logcat_last.txt")
            with open(logcat_last_path, "w", encoding="utf-8") as handle:
                handle.write(last_output)

            log.info("Logcat logs prior to last reboot stored at %s",
                     logcat_last_path)

        self._adb_disconnect()
