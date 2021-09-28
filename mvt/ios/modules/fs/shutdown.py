# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from mvt.common.utils import convert_mactime_to_unix, convert_timestamp_to_iso

from ..base import IOSExtraction

SHUTDOWN_LOG_PATH = [
    "private/var/db/diagnostics/shutdown.log",
]

class ShutdownLog(IOSExtraction):
    """This module extracts processes information from the shutdown log file."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record):
        return {
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": "shutdown",
            "data": f"Client {record['client']} with PID {record['pid']} was running when the device was shut down",
        }
    

    def check_indicators(self):
        if not self.indicators:
            return

        for result in self.results:
            if self.indicators.check_process(result["client"], True):
                self.detected.append(result)

    def run(self):
        self._find_ios_database(root_paths=SHUTDOWN_LOG_PATH)
        self.log.info("Found shutdown log at path: %s", self.file_path)
        
        with open(self.file_path, "r") as shutdown_log:
            shutdown_log_lines = shutdown_log.readlines()
            date = "0000-00-00 00:00:00.000000 (unknown)"

            for line in shutdown_log_lines:
                if line.startswith("After "):
                    continue

                elif line.startswith("\t\tremaining client pid: "):
                    pid = int(line.split("\t\tremaining client pid: ")[1].split(" ")[0])
                    client = line.split("(")[1].split(")")[0]
                    entry = {
                        "isodate": date,
                        "pid": pid,
                        "client": client
                    }
                    if entry not in self.results:
                        self.results.append(entry)

                elif line.startswith("SIGTERM: ["):
                    isodate = int(line.split("[")[1].split("]")[0])
                    date = convert_timestamp_to_iso(convert_mactime_to_unix(isodate, False))

        self.results = sorted(self.results, key=lambda entry: entry["isodate"])
