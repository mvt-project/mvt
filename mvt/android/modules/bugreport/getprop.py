# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import re
from datetime import datetime, timedelta

from mvt.android.parsers import parse_getprop

from .base import BugReportModule

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
        content = self._get_dumpstate_file()
        if not content:
            self.log.error("Unable to find dumpstate file. Did you provide a valid bug report archive?")
            return

        lines = []
        in_getprop = False
        for line in content.decode(errors="ignore").splitlines():
            if line.strip() == "------ SYSTEM PROPERTIES (getprop) ------":
                in_getprop = True
                continue

            if not in_getprop:
                continue

            if line.strip() == "------":
                break

            lines.append(line)

        self.results = parse_getprop("\n".join(lines))

        # Alert if phone is outdated.
        security_patch = self.results.get("ro.build.version.security_patch", "")
        if security_patch:
            patch_date = datetime.strptime(security_patch, "%Y-%m-%d")
            if (datetime.now() - patch_date) > timedelta(days=6*30):
                self.log.warning("This phone has not received security updates for more than "
                                 "six months (last update: %s)", security_patch)

        self.log.info("Extracted %d Android system properties", len(self.results))
