# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional, Union

from mvt.android.modules.adb.packages import (
    DANGEROUS_PERMISSIONS,
    DANGEROUS_PERMISSIONS_THRESHOLD,
    ROOT_PACKAGES,
)
from mvt.android.parsers.dumpsys import parse_dumpsys_packages

from .base import BugReportModule


class Packages(BugReportModule):
    """This module extracts details on receivers for risky activities."""

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

    def serialize(self, record: dict) -> Union[dict, list]:
        records = []

        timestamps = [
            {"event": "package_install", "timestamp": record["timestamp"]},
            {
                "event": "package_first_install",
                "timestamp": record["first_install_time"],
            },
            {"event": "package_last_update", "timestamp": record["last_update_time"]},
        ]

        for timestamp in timestamps:
            records.append(
                {
                    "timestamp": timestamp["timestamp"],
                    "module": self.__class__.__name__,
                    "event": timestamp["event"],
                    "data": f"Install or update of package {record['package_name']}",
                }
            )

        return records

    def check_indicators(self) -> None:
        for result in self.results:
            if result["package_name"] in ROOT_PACKAGES:
                self.log.warning(
                    "Found an installed package related to "
                    'rooting/jailbreaking: "%s"',
                    result["package_name"],
                )
                self.detected.append(result)
                continue

            if not self.indicators:
                continue

            ioc = self.indicators.check_app_id(result.get("package_name"))
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)
                continue

    def run(self) -> None:
        content = self._get_dumpstate_file()
        if not content:
            self.log.error(
                "Unable to find dumpstate file. "
                "Did you provide a valid bug report archive?"
            )
            return

        in_package = False
        in_packages_list = False
        lines = []
        for line in content.decode(errors="ignore").splitlines():
            if line.strip() == "DUMP OF SERVICE package:":
                in_package = True
                continue

            if not in_package:
                continue

            if line.strip() == "Packages:":
                in_packages_list = True
                continue

            if not in_packages_list:
                continue

            if line.strip() == "":
                break

            lines.append(line)

        self.results = parse_dumpsys_packages("\n".join(lines))

        for result in self.results:
            dangerous_permissions_count = 0
            for perm in result["permissions"]:
                if perm["name"] in DANGEROUS_PERMISSIONS:
                    dangerous_permissions_count += 1

            if dangerous_permissions_count >= DANGEROUS_PERMISSIONS_THRESHOLD:
                self.log.info(
                    'Found package "%s" requested %d potentially dangerous permissions',
                    result["package_name"],
                    dangerous_permissions_count,
                )

        self.log.info("Extracted details on %d packages", len(self.results))
