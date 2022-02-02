# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

from .base import AndroidExtraction

log = logging.getLogger(__name__)


class Processes(AndroidExtraction):
    """This module extracts details on running processes."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 serial=None, fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def check_indicators(self):
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_app_id(result.get("name", ""))
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)

    def run(self):
        self._adb_connect()

        output = self._adb_command("ps -e")

        for line in output.splitlines()[1:]:
            line = line.strip()
            if line == "":
                continue

            fields = line.split()
            proc = {
                "user": fields[0],
                "pid": fields[1],
                "parent_pid": fields[2],
                "vsize": fields[3],
                "rss": fields[4],
            }

            # Sometimes WCHAN is empty, so we need to re-align output fields.
            if len(fields) == 8:
                proc["wchan"] = ""
                proc["pc"] = fields[5]
                proc["name"] = fields[7]
            elif len(fields) == 9:
                proc["wchan"] = fields[5]
                proc["pc"] = fields[6]
                proc["name"] = fields[8]

            self.results.append(proc)

        self._adb_disconnect()

        log.info("Extracted records on a total of %d processes", len(self.results))
