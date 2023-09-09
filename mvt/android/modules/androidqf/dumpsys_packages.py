# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Any, Dict, List, Optional, Union

from mvt.android.modules.adb.packages import (
    DANGEROUS_PERMISSIONS,
    DANGEROUS_PERMISSIONS_THRESHOLD,
    ROOT_PACKAGES,
)
from mvt.android.parsers.dumpsys import parse_dumpsys_packages

from .base import AndroidQFModule


class DumpsysPackages(AndroidQFModule):
    """This module analyse dumpsys packages"""

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        module_options: Optional[dict] = None,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[List[Dict[str, Any]]] = None,
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
        entries = []
        for entry in ["timestamp", "first_install_time", "last_update_time"]:
            if entry in record:
                entries.append(
                    {
                        "timestamp": record[entry],
                        "module": self.__class__.__name__,
                        "event": entry,
                        "data": f"Package {record['package_name']} "
                        f"({record['uid']})",
                    }
                )

        return entries

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

            ioc = self.indicators.check_app_id(result.get("package_name", ""))
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)

    def run(self) -> None:
        dumpsys_file = self._get_files_by_pattern("*/dumpsys.txt")
        if len(dumpsys_file) != 1:
            self.log.info("Dumpsys file not found")
            return

        data = self._get_file_content(dumpsys_file[0])

        package = []
        in_service = False
        in_package_list = False
        for line in data.decode("utf-8").split("\n"):
            if line.strip().startswith("DUMP OF SERVICE package:"):
                in_service = True
                continue

            if in_service and line.startswith("Packages:"):
                in_package_list = True
                continue

            if not in_service or not in_package_list:
                continue

            if line.strip() == "":
                break

            package.append(line)

        self.results = parse_dumpsys_packages("\n".join(package))

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
