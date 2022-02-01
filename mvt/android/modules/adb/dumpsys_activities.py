# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

from .base import AndroidExtraction

log = logging.getLogger(__name__)


class DumpsysActivities(AndroidExtraction):
    """This module extracts details on receivers for risky activities."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 serial=None, fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

        self.results = results if results else {}

    def check_indicators(self):
        if not self.indicators:
            return

        for intent, activities in self.results.items():
            for activity in activities:
                ioc = self.indicators.check_app_id(activity["package_name"])
                if ioc:
                    activity["matched_indicator"] = ioc
                    self.detected.append({intent: activity})
                    continue

    @staticmethod
    def parse_activity_resolver_table(output):
        results = {}

        in_activity_resolver_table = False
        in_non_data_actions = False
        intent = None
        for line in output.split("\n"):
            if line.startswith("Activity Resolver Table:"):
                in_activity_resolver_table = True
                continue

            if not in_activity_resolver_table:
                continue

            if line.startswith("  Non-Data Actions:"):
                in_non_data_actions = True
                continue

            if not in_non_data_actions:
                continue

            # If we hit an empty line, the Non-Data Actions section should be
            # finished.
            if line.strip() == "":
                break

            # We detect the action name.
            if line.startswith(" " * 6) and not line.startswith(" " * 8) and ":" in line:
                intent = line.strip().replace(":", "")
                results[intent] = []
                continue

            # If we are not in an intent block yet, skip.
            if not intent:
                continue

            # If we are in a block but the line does not start with 8 spaces
            # it means the block ended a new one started, so we reset and
            # continue.
            if not line.startswith(" " * 8):
                intent = None
                continue

            # If we got this far, we are processing receivers for the
            # activities we are interested in.
            activity = line.strip().split(" ")[1]
            package_name = activity.split("/")[0]

            results[intent].append({
                "package_name": package_name,
                "activity": activity,
            })

        return results

    def run(self):
        self._adb_connect()

        output = self._adb_command("dumpsys package")
        self.results = self.parse_activity_resolver_table(output)

        self._adb_disconnect()
