# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from .artifact import AndroidArtifact


class DumpsysBatteryHistoryArtifact(AndroidArtifact):
    """
    Parser for dumpsys dattery history events.
    """

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_app_id(result["package_name"])
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)
                continue

    def parse(self, data: str) -> None:
        for line in data.splitlines():
            if line.startswith("Battery History "):
                continue

            if line.strip() == "":
                break

            time_elapsed = line.strip().split(" ", 1)[0]

            event = ""
            if line.find("+job") > 0:
                event = "start_job"
                uid = line[line.find("+job") + 5 : line.find(":")]
                service = line[line.find(":") + 1 :].strip('"')
                package_name = service.split("/")[0]
            elif line.find("-job") > 0:
                event = "end_job"
                uid = line[line.find("-job") + 5 : line.find(":")]
                service = line[line.find(":") + 1 :].strip('"')
                package_name = service.split("/")[0]
            elif line.find("+running +wake_lock=") > 0:
                uid = line[line.find("+running +wake_lock=") + 21 : line.find(":")]
                event = "wake"
                service = (
                    line[line.find("*walarm*:") + 9 :].split(" ")[0].strip('"').strip()
                )
                if service == "" or "/" not in service:
                    continue

                package_name = service.split("/")[0]
            elif (line.find("+top=") > 0) or (line.find("-top") > 0):
                if line.find("+top=") > 0:
                    event = "start_top"
                    top_pos = line.find("+top=")
                else:
                    event = "end_top"
                    top_pos = line.find("-top=")
                colon_pos = top_pos + line[top_pos:].find(":")
                uid = line[top_pos + 5 : colon_pos]
                service = ""
                package_name = line[colon_pos + 1 :].strip('"')
            else:
                continue

            self.results.append(
                {
                    "time_elapsed": time_elapsed,
                    "event": event,
                    "uid": uid,
                    "package_name": package_name,
                    "service": service,
                }
            )
