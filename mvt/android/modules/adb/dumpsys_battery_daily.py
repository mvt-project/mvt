# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

from mvt.android.parsers import parse_dumpsys_battery_daily

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
            "data": f"Recorded update of package {record['package_name']} with vers {record['vers']}"
        }

    def check_indicators(self):
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_app_id(result["package_name"])
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)
                continue

    def run(self):
        self._adb_connect()
        output = self._adb_command("dumpsys batterystats --daily")
        self._adb_disconnect()

        self.results = parse_dumpsys_battery_daily(output)

        self.log.info("Extracted %d records from battery daily stats", len(self.results))
