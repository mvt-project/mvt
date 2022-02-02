# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

from .base import AndroidExtraction

log = logging.getLogger(__name__)


class DumpsysBatteryHistory(AndroidExtraction):
    """This module extracts records from battery history events."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 serial=None, fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def check_indicators(self):
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_app_id(result["package_name"])
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)
                continue

    @staticmethod
    def parse_battery_history(output):
        results = []

        for line in output.splitlines()[1:]:
            if line.strip() == "":
                break

            time_elapsed, rest = line.strip().split(" ", 1)

            start = line.find(" 100 ")
            if start == -1:
                continue

            line = line[start+5:]

            event = ""
            if line.startswith("+job"):
                event = "start_job"
            elif line.startswith("-job"):
                event = "end_job"
            elif line.startswith("+running +wake_lock="):
                event = "wake"
            else:
                continue

            if event in ["start_job", "end_job"]:
                uid = line[line.find("=")+1:line.find(":")]
                service = line[line.find(":")+1:].strip('"')
                package_name = service.split("/")[0]
            elif event == "wake":
                uid = line[line.find("=")+1:line.find(":")]
                service = line[line.find("*walarm*:")+9:].split(" ")[0].strip('"').strip()
                if service == "" or "/" not in service:
                    continue

                package_name = service.split("/")[0]
            else:
                continue

            results.append({
                "time_elapsed": time_elapsed,
                "event": event,
                "uid": uid,
                "package_name": package_name,
                "service": service,
            })

        return results

    def run(self):
        self._adb_connect()

        output = self._adb_command("dumpsys batterystats --history")
        self.results = self.parse_battery_history(output)

        self.log.info("Extracted %d records from battery history", len(self.results))

        self._adb_disconnect()
