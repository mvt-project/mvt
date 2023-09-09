# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from typing import Union

from .artifact import AndroidArtifact


class DumpsysBatteryDailyArtifact(AndroidArtifact):
    """
    Parser for dumpsys dattery daily updates.
    """

    def serialize(self, record: dict) -> Union[dict, list]:
        return {
            "timestamp": record["from"],
            "module": self.__class__.__name__,
            "event": "battery_daily",
            "data": f"Recorded update of package {record['package_name']} "
            f"with vers {record['vers']}",
        }

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_app_id(result["package_name"])
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)
                continue

    def parse(self, output: str) -> None:
        daily = None
        daily_updates = []
        for line in output.splitlines():
            if line.startswith("  Daily from "):
                if len(daily_updates) > 0:
                    self.results.extend(daily_updates)
                    daily_updates = []

                timeframe = line[13:].strip()
                date_from, date_to = timeframe.strip(":").split(" to ", 1)
                daily = {"from": date_from[0:10], "to": date_to[0:10]}
                continue

            if not daily:
                continue

            if not line.strip().startswith("Update "):
                continue

            line = line.strip().replace("Update ", "")
            package_name, vers = line.split(" ", 1)
            vers_nr = vers.split("=", 1)[1]

            already_seen = False
            for update in daily_updates:
                if package_name == update["package_name"] and vers_nr == update["vers"]:
                    already_seen = True
                    break

            if not already_seen:
                daily_updates.append(
                    {
                        "action": "update",
                        "from": daily["from"],
                        "to": daily["to"],
                        "package_name": package_name,
                        "vers": vers_nr,
                    }
                )

        if len(daily_updates) > 0:
            self.results.extend(daily_updates)
