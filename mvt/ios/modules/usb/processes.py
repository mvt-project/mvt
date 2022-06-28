# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

from pymobiledevice3.services.os_trace import OsTraceService

from .base import IOSUSBExtraction


class Processes(IOSUSBExtraction):
    """This class extracts all processes running on the phone."""
    def __init__(self, file_path: str = None, target_path: str = None,
                 results_path: str = None, fast_mode: bool = False,
                 log: logging.Logger = None, results: list = []) -> None:
        super().__init__(file_path=file_path, target_path=target_path,
                         results_path=results_path, fast_mode=fast_mode,
                         log=log, results=results)

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_process(result["name"])
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)

    def run(self) -> None:
        processes = OsTraceService(lockdown=self.lockdown).get_pid_list().get('Payload')
        for p in processes:
            self.results.append({
                "pid": p,
                "name": processes[p]["ProcessName"]
            })

        self.log.info("{} running processes identified on the phone".format(len(self.results)))
