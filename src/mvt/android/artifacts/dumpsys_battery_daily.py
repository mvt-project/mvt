# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from typing import Any

from mvt.common.module_types import ModuleAtomicResult, ModuleSerializedResult

from .artifact import AndroidArtifact


class DumpsysBatteryDailyArtifact(AndroidArtifact):
    """
    Parser for dumpsys dattery daily updates.
    """

    def serialize(self, record: ModuleAtomicResult) -> ModuleSerializedResult:
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
            ioc_match = self.indicators.check_app_id(result["package_name"])
            if ioc_match:
                self.alertstore.critical(
                    ioc_match.message, "", result, matched_indicator=ioc_match.ioc
                )
                continue

    def parse(self, output: str) -> None:
        daily = None
        daily_updates: list[dict[str, Any]] = []
        package_versions: dict[
            str, str
        ] = {}  # Track package versions to detect downgrades
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
                update_record: dict[str, Any] = {
                    "action": "update",
                    "from": daily["from"],
                    "to": daily["to"],
                    "package_name": package_name,
                    "vers": vers_nr,
                }

                # Check for uninstall (version 0)
                if vers_nr == "0":
                    self.alertstore.medium(
                        f"Detected uninstall of package {package_name} (vers 0)",
                        daily["from"],
                        update_record,
                    )
                # Check for downgrade
                elif package_name in package_versions:
                    try:
                        current_vers = int(vers_nr)
                        previous_vers = int(package_versions[package_name])
                        if current_vers < previous_vers:
                            update_record["action"] = "downgrade"
                            update_record["previous_vers"] = str(previous_vers)
                            self.alertstore.medium(
                                f"Detected downgrade of package {package_name} "
                                f"from vers {previous_vers} to vers {current_vers}",
                                daily["from"],
                                update_record,
                            )
                    except ValueError:
                        # If version numbers aren't integers, skip comparison
                        pass

                # Update tracking dictionary
                package_versions[package_name] = vers_nr

                daily_updates.append(update_record)

        if len(daily_updates) > 0:
            self.results.extend(daily_updates)
