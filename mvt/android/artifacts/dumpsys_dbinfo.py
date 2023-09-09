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
                ioc = self.indicators.check_app_id(part)
                if ioc:
                    result["matched_indicator"] = ioc
                    self.detected.append(result)
                    continue

    def parse(self, output: str) -> None:
        rxp = re.compile(
            r".*\[([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3})\].*\[Pid:\((\d+)\)\](\w+).*sql\=\"(.+?)\""
        )  # pylint: disable=line-too-long
        rxp_no_pid = re.compile(
            r".*\[([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3})\][ ]{1}(\w+).*sql\=\"(.+?)\""
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

            matches = rxp.findall(line)
            if not matches:
                matches = rxp_no_pid.findall(line)
                if not matches:
                    continue

                match = matches[0]
                self.results.append(
                    {
                        "isodate": match[0],
                        "action": match[1],
                        "sql": match[2],
                        "path": pool,
                    }
                )
            else:
                match = matches[0]
                self.results.append(
                    {
                        "isodate": match[0],
                        "pid": match[1],
                        "action": match[2],
                        "sql": match[3],
                        "path": pool,
                    }
                )
