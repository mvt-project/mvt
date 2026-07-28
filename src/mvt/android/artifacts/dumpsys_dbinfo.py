# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import re

from .artifact import AndroidArtifact


class DumpsysDBInfoArtifact(AndroidArtifact):
    """
    Parser for dumpsys DBInfo service
    """

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            path = result.get("path", "")
            for part in path.split("/"):
                ioc_match = self.indicators.check_app_id(part)
                if ioc_match:
                    self.alertstore.critical(
                        ioc_match.message, "", result, matched_indicator=ioc_match.ioc
                    )
                    continue

    def parse(self, output: str) -> None:
        rxp = re.compile(
            r".*\[((?:[0-9]{4}-)?[0-9]{2}-[0-9]{2} "
            r"[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3})\]\s*"
            r"(?:\[Pid:\((\d+)\)\])?([\w-]+).*?sql=\"(.+?)\""
        )  # pylint: disable=line-too-long

        pool = None
        in_operations = False
        for line in output.splitlines():
            if line.startswith("Connection pool for "):
                pool = line.replace("Connection pool for ", "").rstrip(":")

            if not pool:
                continue

            if line.strip() == "Most recently executed operations:":
                in_operations = True
                continue

            if not in_operations:
                continue

            if not line.startswith("        "):
                in_operations = False
                pool = None
                continue

            match = rxp.match(line)
            if not match:
                continue

            result = {
                "isodate": match.group(1),
                "action": match.group(3),
                "sql": match.group(4),
                "path": pool,
            }
            if match.group(2):
                result["pid"] = match.group(2)
            self.results.append(result)
