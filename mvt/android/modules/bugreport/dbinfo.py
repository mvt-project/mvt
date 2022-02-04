# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

from mvt.android.parsers import parse_dumpsys_dbinfo

from .base import BugReportModule

log = logging.getLogger(__name__)


class DBInfo(BugReportModule):
    """This module extracts records from battery daily updates."""

    slug = "dbinfo"

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 serial=None, fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def check_indicators(self):
        if not self.indicators:
            return

        for result in self.results:
            path = result.get("path", "")
            for part in path.split("/"):
                ioc = self.indicators.check_app_id(part)
                if ioc:
                    result["matched_indicator"] = ioc
                    self.detected.append(result)
                    continue

    def run(self):
        content = self._get_dumpstate_file()
        if not content:
            self.log.error("Unable to find dumpstate file. Did you provide a valid bug report archive?")
            return

        in_dbinfo = False
        lines = []
        for line in content.decode(errors="ignore").splitlines():
            if line.strip() == "DUMP OF SERVICE dbinfo:":
                in_dbinfo = True
                continue

            if not in_dbinfo:
                continue

            if line.strip().startswith("------------------------------------------------------------------------------"):
                break

            lines.append(line)

        self.results = parse_dumpsys_dbinfo("\n".join(lines))

        self.log.info("Extracted a total of %d database connection pool records",
                      len(self.results))
