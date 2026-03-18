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
        action = record.get("action", "update")
        package_name = record["package_name"]
        vers = record["vers"]

        if vers == "0":
            data = f"Recorded uninstall of package {package_name} (vers 0)"
        elif action == "downgrade":
            prev_vers = record.get("previous_vers", "unknown")
            data = f"Recorded downgrade of package {package_name} from vers {prev_vers} to vers {vers}"
        else:
            data = f"Recorded update of package {package_name} with vers {vers}"

        return {
            "timestamp": record["from"],
            "module": self.__class__.__name__,
            "event": "battery_daily",
            "data": data,
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
        package_versions = {}  # Track package versions to detect downgrades
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
                update_record = {
                    "action": "update",
                    "from": daily["from"],
                    "to": daily["to"],
                    "package_name": package_name,
                    "vers": vers_nr,
                }

                # Check for uninstall (version 0)
                if vers_nr == "0":
                    self.log.warning(
                        "Detected uninstall of package %s (vers 0) on %s",
                        package_name,
                        daily["from"],
                    )
                # Check for downgrade
                elif package_name in package_versions:
                    try:
                        current_vers = int(vers_nr)
                        previous_vers = int(package_versions[package_name])
                        if current_vers < previous_vers:
                            update_record["action"] = "downgrade"
                            update_record["previous_vers"] = str(previous_vers)
                            self.log.warning(
                                "Detected downgrade of package %s from vers %d to vers %d on %s",
                                package_name,
                                previous_vers,
                                current_vers,
                                daily["from"],
                            )
                    except ValueError:
                        # If version numbers aren't integers, skip comparison
                        pass

                # Update tracking dictionary
                package_versions[package_name] = vers_nr

                daily_updates.append(update_record)

        if len(daily_updates) > 0:
            self.results.extend(daily_updates)
