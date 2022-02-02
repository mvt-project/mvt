# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import re

from .base import BugReportModule
from mvt.android.modules.adb.getprop import Getprop as GP

log = logging.getLogger(__name__)


class Getprop(BugReportModule):
    """This module extracts device properties from getprop command."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 serial=None, fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

        self.results = {} if not results else results

    def run(self):
        dumpstate_files = self._get_files_by_pattern("dumpstate-*")
        if not dumpstate_files:
            return

        content = self._get_file_content(dumpstate_files[0])
        if not content:
            return

        lines = []
        in_getprop = False
        for line in content.decode().splitlines():
            if line.strip() == "------ SYSTEM PROPERTIES (getprop) ------":
                in_getprop = True
                continue

            if not in_getprop:
                continue

            if line.strip() == "------":
                break

            lines.append(line)

        self.results = GP.parse_getprop("\n".join(lines))

        self.log.info("Extracted %d Android system properties", len(self.results))

