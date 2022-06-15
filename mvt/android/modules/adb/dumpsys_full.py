# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os

from .base import AndroidExtraction

log = logging.getLogger(__name__)


class DumpsysFull(AndroidExtraction):
    """This module extracts stats on battery consumption by processes."""

    def __init__(self, file_path=None, target_path=None, results_path=None,
                 serial=None, fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, target_path=target_path,
                         results_path=results_path, fast_mode=fast_mode,
                         log=log, results=results)

    def run(self):
        self._adb_connect()

        output = self._adb_command("dumpsys")
        if self.results_path:
            output_path = os.path.join(self.results_path, "dumpsys.txt")
            with open(output_path, "w", encoding="utf-8") as handle:
                handle.write(output)

            log.info("Full dumpsys output stored at %s", output_path)

        self._adb_disconnect()
