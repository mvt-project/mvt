# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

from mvt.android.parsers import parse_dumpsys_activity_resolver_table

from .base import AndroidExtraction

log = logging.getLogger(__name__)


class DumpsysActivities(AndroidExtraction):
    """This module extracts details on receivers for risky activities."""

    def __init__(self, file_path: str = None, target_path: str = None,
                 results_path: str = None, fast_mode: bool = False,
                 log: logging.Logger = None, results: list = []) -> None:
        super().__init__(file_path=file_path, target_path=target_path,
                         results_path=results_path, fast_mode=fast_mode,
                         log=log, results=results)

        self.results = results if results else {}

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for intent, activities in self.results.items():
            for activity in activities:
                ioc = self.indicators.check_app_id(activity["package_name"])
                if ioc:
                    activity["matched_indicator"] = ioc
                    self.detected.append({intent: activity})
                    continue

    def run(self) -> None:
        self._adb_connect()
        output = self._adb_command("dumpsys package")
        self._adb_disconnect()

        self.results = parse_dumpsys_activity_resolver_table(output)

        self.log.info("Extracted activities for %d intents", len(self.results))
