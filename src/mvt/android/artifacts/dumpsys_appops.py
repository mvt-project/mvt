# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from datetime import datetime
import re
from typing import Any

from mvt.common.module_types import ModuleAtomicResult, ModuleSerializedResult
from mvt.common.utils import convert_datetime_to_iso

from .artifact import AndroidArtifact

RISKY_PERMISSIONS = ["REQUEST_INSTALL_PACKAGES"]
RISKY_PACKAGES = ["com.android.shell"]


class DumpsysAppopsArtifact(AndroidArtifact):
    """
    Parser for dumpsys app ops info
    """

    def serialize(self, result: ModuleAtomicResult) -> ModuleSerializedResult:
        records = []
        for perm in result["permissions"]:
            if "entries" not in perm:
                continue

            for entry in perm["entries"]:
                if entry.get("timestamp"):
                    records.append(
                        {
                            "timestamp": entry["timestamp"],
                            "module": self.__class__.__name__,
                            "event": entry["event"],
                            "data": f"{result['package_name']} access to "
                            f"{perm['name']}: {entry['event']}",
                        }
                    )

        return records

    def check_indicators(self) -> None:
        for result in self.results:
            if self.indicators:
                ioc_match = self.indicators.check_app_id(result.get("package_name"))
                if ioc_match:
                    self.alertstore.critical(
                        ioc_match.message, "", result, matched_indicator=ioc_match.ioc
                    )
                    continue

            # We use a placeholder entry to create a basic alert even without permission entries.
            placeholder_entry = {"event": "unknown", "timestamp": ""}

            for perm in result["permissions"]:
                if (
                    perm["name"] in RISKY_PERMISSIONS
                    # and perm["access"] == "allow"
                ):
                    for entry in sorted(
                        perm["entries"] or [placeholder_entry],
                        key=lambda x: x.get("timestamp") or "",
                    ):
                        cleaned_result = result.copy()
                        cleaned_result["permissions"] = [perm]
                        self.alertstore.medium(
                            f"Package '{result['package_name']}' had risky permission '{perm['name']}' set to '{entry['event']}' at {entry['timestamp']}",
                            entry["timestamp"],
                            cleaned_result,
                        )

                elif result["package_name"] in RISKY_PACKAGES:
                    for entry in sorted(
                        perm["entries"] or [placeholder_entry],
                        key=lambda x: x.get("timestamp") or "",
                    ):
                        cleaned_result = result.copy()
                        cleaned_result["permissions"] = [perm]
                        self.alertstore.medium(
                            f"Risky package '{result['package_name']}' had '{perm['name']}' permission set to '{entry['event']}' at {entry['timestamp']}",
                            entry["timestamp"],
                            cleaned_result,
                        )

    def parse(self, output: str) -> None:
        self.results: list[dict[str, Any]] = []
        permission: dict[str, Any] | None = None
        package: dict[str, Any] | None = None
        uid: str | None = None
        uid_details: dict[str, Any] = {}
        attribution: str | None = None
        in_packages = False

        def finish_permission() -> None:
            nonlocal permission
            if package is not None and permission is not None:
                package["permissions"].append(permission)
            permission = None

        def finish_package() -> None:
            nonlocal package
            finish_permission()
            if package is not None:
                self.results.append(package)
            package = None

        for line in output.splitlines():
            uid_match = re.match(r"^  Uid ([^:]+):$", line)
            if uid_match:
                in_packages = True
                finish_package()
                uid = uid_match.group(1)
                uid_details = {
                    "uid_state": None,
                    "capability": None,
                    "app_widget_visible": None,
                    "default_modes": {},
                }
                continue

            if not in_packages:
                continue

            uid_property = re.match(
                r"^    (state|capability|appWidgetVisible)=(.*)$", line
            )
            if uid_property:
                key = {
                    "state": "uid_state",
                    "appWidgetVisible": "app_widget_visible",
                }.get(uid_property.group(1), uid_property.group(1))
                value: Any = uid_property.group(2)
                if value in ("true", "false"):
                    value = value == "true"
                uid_details[key] = value
                continue

            default_mode = re.match(r"^      ([A-Z0-9_]+): mode=([^\s]+)", line)
            if default_mode and package is None:
                uid_details["default_modes"][default_mode.group(1)] = (
                    default_mode.group(2)
                )
                continue

            if line.startswith("    Package "):
                finish_package()
                package = {
                    "package_name": line[12:-1],
                    "permissions": [],
                    "uid": uid,
                    **uid_details,
                }
                continue

            operation_match = re.match(
                r"^      ([A-Z0-9_]+)(?: \(([^)]+)\))?:\s*$", line
            )
            if package is not None and operation_match:
                finish_permission()
                permission = {
                    "name": operation_match.group(1),
                    "mode": operation_match.group(2),
                    "entries": [],
                }
                attribution = None
                continue

            attribution_match = re.match(r"^\s{8,}([^=]+)=\[$", line)
            if attribution_match:
                attribution = attribution_match.group(1).strip()
                continue
            if line.strip() == "]":
                attribution = None
                continue

            if permission is None:
                continue
            event_match = re.match(
                r"^\s*(Access|Reject):\s*\[([^]]+)\]\s*"
                r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)\s*"
                r"(\([^)]*\))?(?:\s+duration=([^\s]+))?",
                line,
            )
            running_match = re.match(
                r"^\s*Running start at:\s*(\S+(?: \S+)?)",
                line,
            )
            if event_match:
                entry = {
                    "event": event_match.group(1).lower(),
                    "access": event_match.group(1),
                    "uid_state": event_match.group(2),
                    "timestamp": convert_datetime_to_iso(
                        datetime.strptime(event_match.group(3), "%Y-%m-%d %H:%M:%S.%f")
                    ),
                    "relative_time": event_match.group(4),
                    "duration": event_match.group(5),
                    "attribution": attribution,
                }
                permission["entries"].append(entry)
            elif running_match:
                raw_start = running_match.group(1)
                timestamp = None
                if re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+", raw_start):
                    timestamp = convert_datetime_to_iso(
                        datetime.strptime(raw_start, "%Y-%m-%d %H:%M:%S.%f")
                    )
                permission["entries"].append(
                    {
                        "event": "running",
                        "access": "Running",
                        "uid_state": None,
                        "timestamp": timestamp,
                        "relative_time": raw_start
                        if raw_start.startswith("+")
                        else None,
                        "duration": None,
                        "attribution": attribution,
                    }
                )

        finish_package()
