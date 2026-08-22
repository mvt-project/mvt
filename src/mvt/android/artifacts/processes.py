# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from .artifact import AndroidArtifact


FIELD_NAMES = {
    "LABEL": "label",
    "USER": "user",
    "PID": "pid",
    "TID": "tid",
    "PPID": "ppid",
    "VSZ": "virtual_memory_size",
    "RSS": "resident_set_size",
    "WCHAN": "wchan",
    "ADDR": "address",
    "S": "state",
    "PRI": "priority",
    "NI": "nice",
    "RTPRIO": "realtime_priority",
    "SCH": "scheduler",
    "PCY": "policy",
    "TIME": "cpu_time",
    "CMD": "command",
    "NAME": "command",
}
INTEGER_FIELDS = {
    "pid",
    "tid",
    "ppid",
    "virtual_memory_size",
    "resident_set_size",
    "priority",
    "nice",
}


class Processes(AndroidArtifact):
    def parse(self, entry: str) -> None:
        self.results = []
        lines = [line for line in entry.splitlines() if line.strip()]
        if not lines:
            return
        headers = lines[0].split()
        if not all(header in FIELD_NAMES for header in headers):
            return

        for line in lines[1:]:
            values = line.split(None, len(headers) - 1)
            if len(values) != len(headers):
                continue
            result = {}
            valid = True
            for header, raw in zip(headers, values):
                key = FIELD_NAMES[header]
                value: str | int = raw.strip("[]") if key == "command" else raw
                if key in INTEGER_FIELDS:
                    try:
                        value = int(value)
                    except ValueError:
                        valid = False
                        break
                result[key] = value
            if valid:
                self.results.append(result)

    def check_indicators(self) -> None:
        if not self.indicators:
            return
        for result in self.results:
            command = result.get("command", "")
            if not isinstance(command, str):
                continue
            process_name = command.rsplit("/", 1)[-1]
            if not process_name or process_name == "gatekeeperd":
                continue
            for checker in (
                self.indicators.check_app_id,
                self.indicators.check_process,
            ):
                ioc_match = checker(process_name)
                if ioc_match:
                    self.alertstore.critical(
                        ioc_match.message,
                        "",
                        result,
                        matched_indicator=ioc_match.ioc,
                    )
                    break
