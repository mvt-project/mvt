# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import re

from mvt.android.parsers.dumpsys import parse_dumpsys_appops

from .base import AndroidExtraction

log = logging.getLogger(__name__)


class DumpsysAppOps(AndroidExtraction):
    """This module extracts records from App-op Manager."""

    slug = "dumpsys_appops"

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 serial=None, fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record):
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
                        "data": f"{record['package_name']} access to {perm['name']} : {entry['access']}",
                    })

        return records

    def check_indicators(self):
        for result in self.results:
            if self.indicators:
                ioc = self.indicators.check_app_id(result.get("package_name"))
                if ioc:
                    result["matched_indicator"] = ioc
                    self.detected.append(result)
                    continue

            for perm in result["permissions"]:
                if perm["name"] == "REQUEST_INSTALL_PACKAGES" and perm["access"] == "allow":
                    self.log.info("Package %s with REQUEST_INSTALL_PACKAGES permission",
                                  result["package_name"])

    def run(self):
        self._adb_connect()
        output = self._adb_command("dumpsys appops")
        self._adb_disconnect()

        self.results = parse_dumpsys_appops(output)

        self.log.info("Extracted a total of %d records from app-ops manager",
                      len(self.results))
