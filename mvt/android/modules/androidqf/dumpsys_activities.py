# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional

from mvt.android.parsers import parse_dumpsys_activity_resolver_table

from .base import AndroidQFModule


class DumpsysActivities(AndroidQFModule):
    """This module extracts details on receivers for risky activities."""

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        fast_mode: bool = False,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[list] = None,
    ) -> None:
        super().__init__(
            file_path=file_path,
            target_path=target_path,
            results_path=results_path,
            fast_mode=fast_mode,
            log=log,
            results=results,
        )

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

    def run(self) -> None:
        dumpsys_file = self._get_files_by_pattern("*/dumpsys.txt")
        if not dumpsys_file:
            return

        lines = []
        in_package = False
        with open(dumpsys_file[0]) as handle:
            for line in handle:
                if line.strip() == "DUMP OF SERVICE package:":
                    in_package = True
                    continue

                if not in_package:
                    continue

                if line.strip().startswith(
                    "------------------------------------------------------------------------------"
                ):  # pylint: disable=line-too-long
                    break

                lines.append(line.rstrip())

        self.results = parse_dumpsys_activity_resolver_table("\n".join(lines))

        self.log.info("Extracted activities for %d intents", len(self.results))
