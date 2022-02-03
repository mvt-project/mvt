# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import re

from mvt.android.parsers import parse_dumpsys_dbinfo

from .base import AndroidExtraction

log = logging.getLogger(__name__)


class DumpsysDBInfo(AndroidExtraction):
    """This module extracts records from battery daily updates."""

    slug = "dumpsys_dbinfo"

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
        self._adb_connect()
        output = self._adb_command("dumpsys dbinfo")
        self._adb_disconnect()

        self.results = parse_dumpsys_dbinfo(output)

        self.log.info("Extracted a total of %d records from database information",
                      len(self.results))
