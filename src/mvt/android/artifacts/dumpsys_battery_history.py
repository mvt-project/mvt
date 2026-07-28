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
            ioc_match = self.indicators.check_app_id(result["package_name"])
            if ioc_match:
                self.alertstore.critical(
                    ioc_match.message, "", result, matched_indicator=ioc_match.ioc
                )
                continue

    def parse(self, data: str) -> None:
        for line in data.splitlines():
            if line.startswith("Battery History "):
                continue

            if line.strip() == "":
                break

            time_parts = line.strip().split()
            time_elapsed = time_parts[0]
            if (
                len(time_parts) > 1
                and len(time_parts[0]) == 5
                and time_parts[0][2] == "-"
                and ":" in time_parts[1]
            ):
                time_elapsed = " ".join(time_parts[:2])

            event = ""
            if line.find("+job") > 0:
                event = "start_job"
                payload = line.split("+job=", 1)[1]
                uid, separator, service = payload.partition(":")
                if not separator:
                    continue
                service = service.strip().strip('"')
                package_name = service.split("/")[0]
            elif line.find("-job") > 0:
                event = "end_job"
                payload = line.split("-job=", 1)[1]
                uid, separator, service = payload.partition(":")
                if not separator:
                    continue
                service = service.strip().strip('"')
                package_name = service.split("/")[0]
            elif line.find("+running +wake_lock=") > 0:
                payload = line.split("+running +wake_lock=", 1)[1]
                uid, separator, _ = payload.partition(":")
                if not separator:
                    continue
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
