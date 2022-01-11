# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import io
import logging
import os

from .base import AndroidExtraction

log = logging.getLogger(__name__)


class DumpsysAccessibility(AndroidExtraction):
    """This module extracts stats on accessibility."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 serial=None, fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def run(self):
        self._adb_connect()

        stats = self._adb_command("dumpsys accessibility")

        in_services = False
        for line in stats.split("\n"):
            if line.strip().startswith("installed services:"):
                in_services = True
                continue

            if not in_services:
                continue

            if line.strip() == "}":
                break

            service = line.split(":")[1].strip()
            log.info("Found installed accessibility service \"%s\"", service)

        if self.output_folder:
            acc_path = os.path.join(self.output_folder,
                                      "dumpsys_accessibility.txt")
            with io.open(acc_path, "w", encoding="utf-8") as handle:
                handle.write(stats)

            log.info("Records from dumpsys accessibility stored at %s",
                     acc_path)

        self._adb_disconnect()
