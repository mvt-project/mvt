# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import re
from typing import Any, Dict, List, Union

from mvt.android.utils import ROOT_PACKAGES

from .artifact import AndroidArtifact


class DumpsysPackagesArtifact(AndroidArtifact):
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

    @staticmethod
    def parse_dumpsys_package_for_details(output: str) -> Dict[str, Any]:
        """
        Parse one entry of a dumpsys package information
        """
        details = {
            "uid": "",
            "version_name": "",
            "version_code": "",
            "timestamp": "",
            "first_install_time": "",
            "last_update_time": "",
            "permissions": [],
            "requested_permissions": [],
        }
        in_install_permissions = False
        in_runtime_permissions = False
        in_declared_permissions = False
        in_requested_permissions = True
        for line in output.splitlines():
            if in_install_permissions:
                if line.startswith(" " * 4) and not line.startswith(" " * 6):
                    in_install_permissions = False
                else:
                    lineinfo = line.strip().split(":")
                    permission = lineinfo[0]
                    granted = None
                    if "granted=" in lineinfo[1]:
                        granted = "granted=true" in lineinfo[1]

                    details["permissions"].append(
                        {"name": permission, "granted": granted, "type": "install"}
                    )
            if in_runtime_permissions:
                if not line.startswith(" " * 8):
                    in_runtime_permissions = False
                else:
                    lineinfo = line.strip().split(":")
                    permission = lineinfo[0]
                    granted = None
                    if "granted=" in lineinfo[1]:
                        granted = "granted=true" in lineinfo[1]

                    details["permissions"].append(
                        {"name": permission, "granted": granted, "type": "runtime"}
                    )
            if in_declared_permissions:
                if not line.startswith(" " * 6):
                    in_declared_permissions = False
                else:
                    permission = line.strip().split(":")[0]
                    details["permissions"].append(
                        {"name": permission, "type": "declared"}
                    )
            if in_requested_permissions:
                if not line.startswith(" " * 6):
                    in_requested_permissions = False
                else:
                    details["requested_permissions"].append(line.strip())
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
            elif line.strip() == "declared permissions:":
                in_declared_permissions = True
            elif line.strip() == "requested permissions:":
                in_requested_permissions = True

        return details

    def parse_dumpsys_packages(self, output: str) -> List[Dict[str, Any]]:
        """
        Parse the dumpsys package service data
        """
        pkg_rxp = re.compile(r"  Package \[(.+?)\].*")

        results = []
        package_name = None
        package = {}
        lines = []
        for line in output.splitlines():
            if line.startswith("  Package ["):
                if len(lines) > 0:
                    details = self.parse_dumpsys_package_for_details("\n".join(lines))
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

        if len(lines) > 0:
            details = self.parse_dumpsys_package_for_details("\n".join(lines))
            package.update(details)
            results.append(package)

        return results

    def parse(self, content: str):
        """
        Parse the Dumpsys Package section for activities
        Adds results to self.results

        :param content: content of the package section (string)
        """
        self.results = []
        package = []

        in_package_list = False
        for line in content.split("\n"):
            if line.startswith("Packages:"):
                in_package_list = True
                continue

            if not in_package_list:
                continue

            if line.strip() == "":
                break

            package.append(line)

        self.results = self.parse_dumpsys_packages("\n".join(package))
