# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional

from mvt.android.parsers import parse_dumpsys_battery_history

from .base import AndroidExtraction


class DumpsysBatteryHistory(AndroidExtraction):
    """This module extracts records from battery history events."""

    def __init__(
        self,
        file_path: Optional[str] = "",
        target_path: Optional[str] = "",
        results_path: Optional[str] = "",
        fast_mode: Optional[bool] = False,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[list] = []
    ) -> None:
        super().__init__(file_path=file_path, target_path=target_path,
                         results_path=results_path, fast_mode=fast_mode,
                         log=log, results=results)

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_app_id(result["package_name"])
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)
                continue

    def run(self) -> None:
        self._adb_connect()
        output = self._adb_command("dumpsys batterystats --history")
        self._adb_disconnect()

        self.results = parse_dumpsys_battery_history(output)

        self.log.info("Extracted %d records from battery history",
                      len(self.results))
