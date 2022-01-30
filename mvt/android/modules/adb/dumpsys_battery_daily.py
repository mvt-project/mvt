# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

from .base import AndroidExtraction

log = logging.getLogger(__name__)


class DumpsysBatteryDaily(AndroidExtraction):
    """This module extracts records from battery daily updates."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 serial=None, fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record):
        return {
            "timestamp": record["from"],
            "module": self.__class__.__name__,
            "event": "battery_daily",
            "data": f"Recorded update of package {record['package']} with vers {record['vers']}"
        }

    def check_indicators(self):
        for result in self.results:
            ioc = self.indicators.check_app_id(result["package"])
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)
                continue

    def process_battery_history(self, output):
        daily = None
        daily_updates = []
        for line in output.split("\n")[1:]:
            if line.startswith("  Daily from "):
                timeframe = line[13:].strip()
                date_from, date_to = timeframe.strip(":").split(" to ", 1)
                daily = {"from": date_from[0:10], "to": date_to[0:10]}

            if not daily:
                continue

            if line.strip() == "":
                self.results.extend(daily_updates)
                daily = None
                daily_updates = []
                continue

            if not line.strip().startswith("Update "):
                continue

            line = line.strip().replace("Update ", "")
            package, vers = line.split(" ", 1)
            vers_nr = vers.split("=", 1)[1]

            already_seen = False
            for update in daily_updates:
                if package == update["package"] and vers_nr == update["vers"]:
                    already_seen = True
                    break

            if not already_seen:
                daily_updates.append({
                    "action": "update",
                    "from": daily["from"],
                    "to": daily["to"],
                    "package": package,
                    "vers": vers_nr,
                })

        self.log.info("Extracted %d records from battery daily stats", len(self.results))

    def run(self):
        self._adb_connect()

        output = self._adb_command("dumpsys batterystats --daily")
        self.process_battery_history(output)

        self._adb_disconnect()
