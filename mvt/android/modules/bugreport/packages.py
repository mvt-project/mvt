# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import re

from mvt.android.modules.adb.packages import (DANGEROUS_PERMISSIONS,
                                              DANGEROUS_PERMISSIONS_THRESHOLD,
                                              ROOT_PACKAGES)

from .base import BugReportModule

log = logging.getLogger(__name__)


class Packages(BugReportModule):
    """This module extracts details on receivers for risky activities."""

    def __init__(self, file_path: str = None, target_path: str = None,
                 results_path: str = None, fast_mode: bool = False,
                 log: logging.Logger = None, results: list = []) -> None:
        super().__init__(file_path=file_path, target_path=target_path,
                         results_path=results_path, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record: dict) -> None:
        records = []

        timestamps = [
            {"event": "package_install", "timestamp": record["timestamp"]},
            {"event": "package_first_install", "timestamp": record["first_install_time"]},
            {"event": "package_last_update", "timestamp": record["last_update_time"]},
        ]

        for ts in timestamps:
            records.append({
                "timestamp": ts["timestamp"],
                "module": self.__class__.__name__,
                "event": ts["event"],
                "data": f"Install or update of package {record['package_name']}",
            })

        return records

    def check_indicators(self) -> None:
        for result in self.results:
            if result["package_name"] in ROOT_PACKAGES:
                self.log.warning("Found an installed package related to rooting/jailbreaking: \"%s\"",
                                 result["package_name"])
                self.detected.append(result)
                continue

            if not self.indicators:
                continue

            ioc = self.indicators.check_app_id(result.get("package_name"))
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)
                continue

    @staticmethod
    def parse_package_for_details(output: str) -> dict:
        details = {
            "uid": "",
            "version_name": "",
            "version_code": "",
            "timestamp": "",
            "first_install_time": "",
            "last_update_time": "",
            "requested_permissions": [],
        }

        in_install_permissions = False
        in_runtime_permissions = False
        for line in output.splitlines():
            if in_install_permissions:
                if line.startswith(" " * 4) and not line.startswith(" " * 6):
                    in_install_permissions = False
                    continue

                permission = line.strip().split(":")[0]
                if permission not in details["requested_permissions"]:
                    details["requested_permissions"].append(permission)

            if in_runtime_permissions:
                if not line.startswith(" " * 8):
                    in_runtime_permissions = False
                    continue

                permission = line.strip().split(":")[0]
                if permission not in details["requested_permissions"]:
                    details["requested_permissions"].append(permission)

            if line.strip().startswith("userId="):
                details["uid"] = line.split("=")[1].strip()
            elif line.strip().startswith("versionName="):
                details["version_name"] = line.split("=")[1].strip()
            elif line.strip().startswith("versionCode="):
                details["version_code"] = line.split("=", 1)[1].strip()
            elif line.strip().startswith("timeStamp="):
                details["timestamp"] = line.split("=")[1].strip()
            elif line.strip().startswith("firstInstallTime="):
                details["first_install_time"] = line.split("=")[1].strip()
            elif line.strip().startswith("lastUpdateTime="):
                details["last_update_time"] = line.split("=")[1].strip()
            elif line.strip() == "install permissions:":
                in_install_permissions = True
            elif line.strip() == "runtime permissions:":
                in_runtime_permissions = True

        return details

    def parse_packages_list(self, output: str) -> list:
        pkg_rxp = re.compile(r"  Package \[(.+?)\].*")

        results = []
        package_name = None
        package = {}
        lines = []
        for line in output.splitlines():
            if line.startswith("  Package ["):
                if len(lines) > 0:
                    details = self.parse_package_for_details("\n".join(lines))
                    package.update(details)
                    results.append(package)
                    lines = []
                    package = {}

                matches = pkg_rxp.findall(line)
                if not matches:
                    continue

                package_name = matches[0]
                package["package_name"] = package_name
                continue

            if not package_name:
                continue

            lines.append(line)

        return results

    def run(self) -> None:
        content = self._get_dumpstate_file()
        if not content:
            self.log.error("Unable to find dumpstate file. Did you provide a valid bug report archive?")
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

        self.results = self.parse_packages_list("\n".join(lines))

        for result in self.results:
            dangerous_permissions_count = 0
            for perm in result["requested_permissions"]:
                if perm in DANGEROUS_PERMISSIONS:
                    dangerous_permissions_count += 1

            if dangerous_permissions_count >= DANGEROUS_PERMISSIONS_THRESHOLD:
                self.log.info("Found package \"%s\" requested %d potentially dangerous permissions",
                              result["package_name"], dangerous_permissions_count)

        self.log.info("Extracted details on %d packages", len(self.results))
