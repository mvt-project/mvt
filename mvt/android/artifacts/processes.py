# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from .artifact import AndroidArtifact


class Processes(AndroidArtifact):
    def parse(self, entry: str) -> None:
        for line in entry.split("\n")[1:]:
            proc = line.split()

            # Skip empty lines
            if len(proc) == 0:
                continue

            # Sometimes WCHAN is empty.
            if len(proc) == 8:
                proc = proc[:5] + [""] + proc[5:]

            # Sometimes there is the security label.
            if proc[0].startswith("u:r"):
                label = proc[0]
                proc = proc[1:]
            else:
                label = ""

            # Sometimes there is no WCHAN.
            if len(proc) < 9:
                proc = proc[:5] + [""] + proc[5:]

            self.results.append(
                {
                    "user": proc[0],
                    "pid": int(proc[1]),
                    "ppid": int(proc[2]),
                    "virtual_memory_size": int(proc[3]),
                    "resident_set_size": int(proc[4]),
                    "wchan": proc[5],
                    "aprocress": proc[6],
                    "stat": proc[7],
                    "proc_name": proc[8].strip("[]"),
                    "label": label,
                }
            )

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            proc_name = result.get("proc_name", "")
            if not proc_name:
                continue

            # Skipping this process because of false positives.
            if result["proc_name"] == "gatekeeperd":
                continue

            ioc = self.indicators.check_app_id(proc_name)
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)
                continue

            ioc = self.indicators.check_process(proc_name)
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)
