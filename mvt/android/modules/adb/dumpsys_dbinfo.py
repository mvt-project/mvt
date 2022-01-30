# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import re

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
        for result in self.results:
            path = result.get("path", "")
            for part in path.split("/"):
                ioc = self.indicators.check_app_id(part)
                if ioc:
                    result["matched_indicators"] = ioc
                    self.detected.append(result)
                    continue

    def process_dbinfo(self, output):
        rxp = re.compile(r'.*\[([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3})\].*\[Pid:\((\d+)\)\](\w+).*sql\=\"(.+?)\".*path\=(.*?$)')

        in_operations = False
        for line in output.split("\n"):
            if line.strip() == "Most recently executed operations:":
                in_operations = True
                continue

            if not in_operations:
                continue

            if not line.startswith("        "):
                in_operations = False
                continue

            matches = rxp.findall(line)
            if not matches:
                continue

            match = matches[0]
            self.results.append({
                "isodate": match[0],
                "pid": match[1],
                "action": match[2],
                "sql": match[3],
                "path": match[4],
            })

    def run(self):
        self._adb_connect()

        output = self._adb_command("dumpsys dbinfo")
        self.process_dbinfo(output)

        self.log.info("Extracted a total of %d records from database information",
                      len(self.results))

        self._adb_disconnect()
