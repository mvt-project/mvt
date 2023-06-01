# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from datetime import datetime, timedelta
from typing import Optional

from mvt.android.parsers import parse_getprop

from .base import AndroidExtraction


class Getprop(AndroidExtraction):
    """This module extracts device properties from getprop command."""

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

        self.results = {} if not results else results

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_android_property_name(result.get("name", ""))
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)

    def run(self) -> None:
        self._adb_connect()
        output = self._adb_command("getprop")
        self._adb_disconnect()

        self.results = parse_getprop(output)

        # Alert if phone is outdated.
        for entry in self.results:
            if entry.get("name", "") != "ro.build.version.security_patch":
                continue
            patch_date = datetime.strptime(entry["value"], "%Y-%m-%d")
            if (datetime.now() - patch_date) > timedelta(days=6 * 30):
                self.log.warning(
                    "This phone has not received security updates "
                    "for more than six months (last update: %s)",
                    entry["value"],
                )

        self.log.info("Extracted %d Android system properties", len(self.results))
