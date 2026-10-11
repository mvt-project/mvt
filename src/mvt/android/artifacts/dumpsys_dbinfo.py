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
            r"^\s*\d+:\s*\[((?:\d{4}-)?\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\]\s*"
            r"(?:\[Pid:\((\d+)\)\])?\s*([\w-]+) took (\d+)ms - ([^,]+),"
            r"\s*sql=\"(.*)\"(?:, path=(.*))?$"
        )

        pool: str | None = None
        connection_number: int | None = None
        is_primary: bool | None = None
        in_operations = False
        for line in output.splitlines():
            if line.startswith("Connection pool for "):
                pool = line.replace("Connection pool for ", "").rstrip(":")
                in_operations = False

            connection_match = re.match(r"\s+Connection #(\d+):", line)
            if connection_match:
                connection_number = int(connection_match.group(1))
                is_primary = None

            if line.strip().startswith("isPrimaryConnection:"):
                is_primary = line.strip().split(":", 1)[1].strip() == "true"

            if not pool:
                continue

            if line.strip() == "Most recently executed operations:":
                in_operations = True
                continue

            if not in_operations:
                continue

            if not line.startswith("        "):
                in_operations = False
                continue

            match = rxp.match(line)
            if not match:
                continue

            result = {
                "timestamp": match.group(1),
                "pid": int(match.group(2)) if match.group(2) else None,
                "action": match.group(3),
                "duration_ms": int(match.group(4)),
                "status": match.group(5),
                "sql": match.group(6),
                "path": match.group(7) or pool,
                "pool_path": pool,
                "connection_number": connection_number,
                "is_primary": is_primary,
            }
            self.results.append(result)
