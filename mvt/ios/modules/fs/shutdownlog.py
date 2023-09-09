# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional, Union

from mvt.common.utils import convert_mactime_to_iso

from ..base import IOSExtraction

SHUTDOWN_LOG_PATH = [
    "private/var/db/diagnostics/shutdown.log",
]


class ShutdownLog(IOSExtraction):
    """This module extracts processes information from the shutdown log file."""

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
        return {
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": "shutdown",
            "data": f"Client {record['client']} with PID {record['pid']} "
            "was running when the device was shut down",
        }

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_file_path(result["client"])
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)
                continue

            for ioc in self.indicators.get_iocs("processes"):
                parts = result["client"].split("/")
                if ioc in parts:
                    self.log.warning(
                        'Found mention of a known malicious process "%s" in '
                        "shutdown.log",
                        ioc,
                    )
                    result["matched_indicator"] = ioc
                    self.detected.append(result)
                    continue

    def process_shutdownlog(self, content):
        current_processes = []
        for line in content.split("\n"):
            line = line.strip()

            if line.startswith("remaining client pid:"):
                current_processes.append(
                    {
                        "pid": line[line.find("pid: ") + 5 : line.find(" (")],
                        "client": line[line.find("(") + 1 : line.find(")")],
                    }
                )
            elif line.startswith("SIGTERM: "):
                try:
                    mac_timestamp = int(line[line.find("[") + 1 : line.find("]")])
                except ValueError:
                    try:
                        start = line.find(" @") + 2
                        mac_timestamp = int(line[start : start + 10])
                    except Exception:
                        mac_timestamp = 0

                isodate = convert_mactime_to_iso(mac_timestamp, from_2001=False)

                for current_process in current_processes:
                    self.results.append(
                        {
                            "isodate": isodate,
                            "pid": current_process["pid"],
                            "client": current_process["client"],
                        }
                    )

                current_processes = []

        self.results = sorted(self.results, key=lambda entry: entry["isodate"])

    def run(self) -> None:
        self._find_ios_database(root_paths=SHUTDOWN_LOG_PATH)
        self.log.info("Found shutdown log at path: %s", self.file_path)
        with open(self.file_path, "r", encoding="utf-8") as handle:
            self.process_shutdownlog(handle.read())
