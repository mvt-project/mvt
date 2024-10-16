# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import re
from typing import Dict, List

from mvt.android.utils import warn_android_patch_level

from .artifact import AndroidArtifact

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


class GetProp(AndroidArtifact):
    def parse(self, entry: str) -> None:
        self.results: List[Dict[str, str]] = []
        rxp = re.compile(r"\[(.+?)\]: \[(.+?)\]")

        for line in entry.splitlines():
            line = line.strip()
            if line == "":
                continue

            matches = re.findall(rxp, line)
            if not matches or len(matches[0]) != 2:
                continue

            entry = {"name": matches[0][0], "value": matches[0][1]}
            self.results.append(entry)

    def check_indicators(self) -> None:
        for entry in self.results:
            if entry["name"] in INTERESTING_PROPERTIES:
                self.log.info("%s: %s", entry["name"], entry["value"])

            if entry["name"] == "ro.build.version.security_patch":
                warn_android_patch_level(entry["value"], self.log)

        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_android_property_name(result.get("name", ""))
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)
