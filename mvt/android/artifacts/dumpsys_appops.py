# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from datetime import datetime
from typing import Any, Dict, List, Union

from mvt.common.utils import convert_datetime_to_iso

from .artifact import AndroidArtifact


class DumpsysAppopsArtifact(AndroidArtifact):
    """
    Parser for dumpsys app ops info
    """

    def serialize(self, record: dict) -> Union[dict, list]:
        records = []
        for perm in record["permissions"]:
            if "entries" not in perm:
                continue

            for entry in perm["entries"]:
                if "timestamp" in entry:
                    records.append(
                        {
                            "timestamp": entry["timestamp"],
                            "module": self.__class__.__name__,
                            "event": entry["access"],
                            "data": f"{record['package_name']} access to "
                            f"{perm['name']}: {entry['access']}",
                        }
                    )

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
                if (
                    perm["name"] == "REQUEST_INSTALL_PACKAGES"
                    and perm["access"] == "allow"
                ):
                    self.log.info(
                        "Package %s with REQUEST_INSTALL_PACKAGES " "permission",
                        result["package_name"],
                    )

    def parse(self, output: str) -> None:
        self.results: List[Dict[str, Any]] = []
        perm = {}
        package = {}
        entry = {}
        uid = None
        in_packages = False

        for line in output.splitlines():
            if line.startswith("  Uid 0:"):
                in_packages = True

            if not in_packages:
                continue

            if line.startswith("  Uid "):
                uid = line[6:-1]
                if entry:
                    perm["entries"].append(entry)
                    entry = {}
                if package:
                    if perm:
                        package["permissions"].append(perm)

                    perm = {}
                    self.results.append(package)
                package = {}
                continue

            if line.startswith("    Package "):
                if entry:
                    perm["entries"].append(entry)
                    entry = {}

                if package:
                    if perm:
                        package["permissions"].append(perm)

                    perm = {}
                    self.results.append(package)

                package = {
                    "package_name": line[12:-1],
                    "permissions": [],
                    "uid": uid,
                }
                continue

            if package and line.startswith("      ") and line[6] != " ":
                if entry:
                    perm["entries"].append(entry)
                    entry = {}
                if perm:
                    package["permissions"].append(perm)
                    perm = {}

                perm["name"] = line.split()[0]
                perm["entries"] = []
                if len(line.split()) > 1:
                    perm["access"] = line.split()[1][1:-2]

                continue

            if line.startswith("          "):
                # Permission entry like:
                # Reject: [fg-s]2021-05-19 22:02:52.054 (-314d1h25m2s33ms)
                if entry:
                    perm["entries"].append(entry)
                    entry = {}

                entry["access"] = line.split(":")[0].strip()
                entry["type"] = line[line.find("[") + 1 : line.find("]")]

                try:
                    entry["timestamp"] = convert_datetime_to_iso(
                        datetime.strptime(
                            line[line.find("]") + 1 : line.find("(")].strip(),
                            "%Y-%m-%d %H:%M:%S.%f",
                        )
                    )
                except ValueError:
                    # Invalid date format
                    pass

            if line.strip() == "":
                break

        if entry:
            perm["entries"].append(entry)
        if perm:
            package["permissions"].append(perm)
        if package:
            self.results.append(package)
