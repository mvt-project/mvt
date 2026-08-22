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
        vers = record["version_code"]

        if vers == 0:
            data = f"Recorded uninstall of package {package_name} (vers 0)"
        elif action == "downgrade":
            prev_vers = record.get("previous_version_code", "unknown")
            data = f"Recorded downgrade of package {package_name} from vers {prev_vers} to vers {vers}"
        else:
            data = f"Recorded update of package {package_name} with vers {vers}"

        return {
            "timestamp": record["period_start"],
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
        self.results = []
        daily = None
        daily_updates: list[dict[str, Any]] = []
        records: list[dict[str, Any]] = []
        for line in output.splitlines():
            if line.startswith("  Daily from "):
                if len(daily_updates) > 0:
                    records.extend(daily_updates)
                    daily_updates = []

                timeframe = line[13:].strip()
                date_from, date_to = timeframe.strip(":").split(" to ", 1)
                daily = {
                    "period_start": self._format_daily_timestamp(date_from),
                    "period_end": self._format_daily_timestamp(date_to),
                }
                continue

            if not daily:
                continue

            if not line.strip().startswith("Update "):
                continue

            line = line.strip().replace("Update ", "")
            package_name, vers = line.split(" ", 1)
            vers_raw = vers.split("=", 1)[1]
            try:
                version_code: int | str = int(vers_raw)
            except ValueError:
                version_code = vers_raw

            already_seen = False
            for update in daily_updates:
                if (
                    package_name == update["package_name"]
                    and version_code == update["version_code"]
                ):
                    update["occurrences"] += 1
                    already_seen = True
                    break

            if not already_seen:
                update_record: dict[str, Any] = {
                    "action": "update",
                    "period_start": daily["period_start"],
                    "period_end": daily["period_end"],
                    "package_name": package_name,
                    "version_code": version_code,
                    "occurrences": 1,
                }

                daily_updates.append(update_record)

        if len(daily_updates) > 0:
            records.extend(daily_updates)

        self._detect_uninstalls_and_downgrades(records)
        self.results.extend(records)

    @staticmethod
    def _format_daily_timestamp(value: str) -> str:
        if len(value) >= 19 and value[10] == "-":
            return f"{value[:10]} {value[11:].replace('-', ':')}"
        return value

    def _detect_uninstalls_and_downgrades(self, records: list[dict[str, Any]]) -> None:
        package_versions: dict[str, int] = {}

        for record in sorted(
            records,
            key=lambda record: (
                record["period_start"],
                record["period_end"],
                record["package_name"],
            ),
        ):
            package_name = record["package_name"]
            vers_nr = record["version_code"]

            if vers_nr == 0:
                record["action"] = "uninstall"
                self.alertstore.medium(
                    f"Detected uninstall of package {package_name} (vers 0)",
                    record["period_start"],
                    record,
                )
                package_versions.pop(package_name, None)
                continue

            try:
                current_vers = int(vers_nr)
            except ValueError:
                continue

            previous_vers = package_versions.get(package_name)
            if previous_vers is not None and current_vers < previous_vers:
                record["action"] = "downgrade"
                record["previous_version_code"] = previous_vers
                self.alertstore.medium(
                    f"Detected downgrade of package {package_name} "
                    f"from vers {previous_vers} to vers {current_vers}",
                    record["period_start"],
                    record,
                )

            package_versions[package_name] = current_vers
