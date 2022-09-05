# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional, Union

from mvt.android.parsers import parse_dumpsys_appops

from .base import AndroidQFModule


class DumpsysAppops(AndroidQFModule):

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        fast_mode: Optional[bool] = False,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[list] = None
    ) -> None:
        super().__init__(file_path=file_path, target_path=target_path,
                         results_path=results_path, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record: dict) -> Union[dict, list]:
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
                        "data": f"{record['package_name']} access to "
                                f"{perm['name']} : {entry['access']}",
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
                if (perm["name"] == "REQUEST_INSTALL_PACKAGES"
                        and perm["access"] == "allow"):
                    self.log.info("Package %s with REQUEST_INSTALL_PACKAGES permission",
                                  result["package_name"])

    def run(self) -> None:
        dumpsys_file = self._get_files_by_pattern("*/dumpsys.txt")
        if not dumpsys_file:
            return

        lines = []
        in_package = False
        with open(dumpsys_file[0]) as handle:
            for line in handle:
                if line.startswith("DUMP OF SERVICE appops:"):
                    in_package = True
                    continue

                if in_package:
                    if line.startswith("-------------------------------------------------------------------------------"):  # pylint: disable=line-too-long
                        break

                    lines.append(line.rstrip())

        self.results = parse_dumpsys_appops("\n".join(lines))
        self.log.info("Identified %d applications in AppOps Manager",
                      len(self.results))
