# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os

from .base import AndroidExtraction

log = logging.getLogger(__name__)

class DumpsysBatterystats(AndroidExtraction):
    """This module extracts stats on battery consumption by processes."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 serial=None, fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def run(self):
        self._adb_connect()

        stats = self._adb_command("dumpsys batterystats")
        if self.output_folder:
            stats_path = os.path.join(self.output_folder,
                                      "dumpsys_batterystats.txt")
            with open(stats_path, "w") as handle:
                handle.write(stats)

            log.info("Records from dumpsys batterystats stored at %s",
                      stats_path)

        history = self._adb_command("dumpsys batterystats --history")
        if self.output_folder:
            history_path = os.path.join(self.output_folder,
                                        "dumpsys_batterystats_history.txt")
            with open(history_path, "w") as handle:
                handle.write(history)

            log.info("History records from dumpsys batterystats stored at %s",
                     history_path)

        self._adb_disconnect()
