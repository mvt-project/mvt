# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import re

from .base import BugReportModule

log = logging.getLogger(__name__)


class Packages(BugReportModule):
    """This module extracts details on receivers for risky activities."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 serial=None, fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record):
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

    def check_indicators(self):
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_app_id(result["package_name"])
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)
                continue

    @staticmethod
    def parse_package_for_details(output):
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

    def parse_packages_list(self, output):
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

    def run(self):
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

        self.log.info("Extracted details on %d packages", len(self.results))
