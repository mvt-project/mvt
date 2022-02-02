# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import re

from mvt.android.modules.adb.packages import Packages as PCK
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
    def parse_packages_list(output):
        pkg_rxp = re.compile(r"  Package \[(.+?)\].*")

        results = []
        package_name = None
        package = {}
        lines = []
        for line in output.split("\n"):
            if line.startswith("  Package ["):
                if len(lines) > 0:
                    details = PCK.parse_package_for_details("\n".join(lines))
                    package.update(details)
                    results.append(package)
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
        dumpstate_files = self._get_files_by_pattern("dumpstate-*")
        if not dumpstate_files:
            return

        content = self._get_file_content(dumpstate_files[0])
        if not content:
            return

        in_package = False
        in_packages_list = False
        lines = []
        for line in content.decode().split("\n"):
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
