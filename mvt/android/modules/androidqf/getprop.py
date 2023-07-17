# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from datetime import datetime, timedelta
from typing import Optional

from mvt.android.parsers.getprop import parse_getprop

from .base import AndroidQFModule

INTERESTING_PROPERTIES = [
    "gsm.sim.operator.alpha",
    "gsm.sim.operator.iso-country",
    "persist.sys.timezone",
    "ro.boot.serialno",
    "ro.build.version.sdk",
    "ro.build.version.security_patch",
    "ro.product.cpu.abi",
    "ro.product.locale",
    "ro.product.vendor.manufacturer",
    "ro.product.vendor.model",
    "ro.product.vendor.name",
]


class Getprop(AndroidQFModule):
    """This module extracts data from get properties."""

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        module_options: Optional[dict] = None,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[list] = None,
    ) -> None:
        super().__init__(
            file_path=file_path,
            target_path=target_path,
            results_path=results_path,
            module_options=module_options,
            log=log,
            results=results,
        )
        self.results = []

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_android_property_name(result.get("name", ""))
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)

    def run(self) -> None:
        getprop_files = self._get_files_by_pattern("*/getprop.txt")
        if not getprop_files:
            self.log.info("getprop.txt file not found")
            return

        with open(getprop_files[0]) as f:
            data = f.read()

        self.results = parse_getprop(data)
        for entry in self.results:
            if entry["name"] in INTERESTING_PROPERTIES:
                self.log.info("%s: %s", entry["name"], entry["value"])
            if entry["name"] == "ro.build.version.security_patch":
                last_patch = datetime.strptime(entry["value"], "%Y-%m-%d")
                if (datetime.now() - last_patch) > timedelta(days=6 * 31):
                    self.log.warning(
                        "This phone has not received security "
                        "updates for more than six months "
                        "(last update: %s)",
                        entry["value"],
                    )

        self.log.info("Extracted a total of %d properties", len(self.results))
