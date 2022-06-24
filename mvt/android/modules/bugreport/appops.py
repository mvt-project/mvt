# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

from mvt.android.parsers import parse_dumpsys_appops

from .base import BugReportModule

log = logging.getLogger(__name__)


class Appops(BugReportModule):
    """This module extracts information on package from App-Ops Manager."""

    def __init__(self, file_path: str = None, target_path: str = None,
                 results_path: str = None, fast_mode: bool = False,
                 log: logging.Logger = None, results: list = []) -> None:
        super().__init__(file_path=file_path, target_path=target_path,
                         results_path=results_path, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record: dict) -> None:
        records = []
        for perm in record["permissions"]:
            if "entries" not in perm:
                continue

            for entry in perm["entries"]:
                if "timestamp" in entry:
                    records.append({
                        "timestamp": entry["timestamp"],
                        "module": self.__class__.__name__,
                        "event": entry["access"],
                        "data": f"{record['package_name']} access to {perm['name']}: {entry['access']}",
                    })

        return records

    def check_indicators(self) -> None:
        for result in self.results:
            if self.indicators:
                ioc = self.indicators.check_app_id(result.get("package_name"))
                if ioc:
                    result["matched_indicator"] = ioc
                    self.detected.append(result)
                    continue

            for perm in result["permissions"]:
                if perm["name"] == "REQUEST_INSTALL_PACKAGES" and perm["access"] == "allow":
                    self.log.info("Package %s with REQUEST_INSTALL_PACKAGES permission", result["package_name"])

    def run(self) -> None:
        content = self._get_dumpstate_file()
        if not content:
            self.log.error("Unable to find dumpstate file. Did you provide a valid bug report archive?")
            return

        lines = []
        in_appops = False
        for line in content.decode(errors="ignore").splitlines():
            if line.strip() == "DUMP OF SERVICE appops:":
                in_appops = True
                continue

            if not in_appops:
                continue

            if line.strip().startswith("------------------------------------------------------------------------------"):
                break

            lines.append(line)

        self.results = parse_dumpsys_appops("\n".join(lines))

        self.log.info("Identified a total of %d packages in App-Ops Manager",
                      len(self.results))
