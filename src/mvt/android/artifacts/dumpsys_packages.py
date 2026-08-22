# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import re
from typing import Any

from mvt.android.utils import ROOT_PACKAGES
from mvt.common.module_types import ModuleAtomicResult, ModuleSerializedResult

from .artifact import AndroidArtifact


def _value(raw: str) -> Any:
    if raw == "null":
        return None
    if raw in ("true", "false"):
        return raw == "true"
    try:
        return int(raw)
    except ValueError:
        return raw


class DumpsysPackagesArtifact(AndroidArtifact):
    def check_indicators(self) -> None:
        alerted_root_packages = set()
        for result in self.results:
            package_name = result["package_name"]
            if (
                package_name in ROOT_PACKAGES
                and package_name not in alerted_root_packages
            ):
                alerted_root_packages.add(package_name)
                self.alertstore.medium(
                    f'Found an installed package related to rooting/jailbreaking: "{package_name}"',
                    "",
                    result,
                )
            if not self.indicators:
                continue
            ioc_match = self.indicators.check_app_id(package_name)
            if ioc_match:
                self.alertstore.critical(
                    ioc_match.message, "", result, matched_indicator=ioc_match.ioc
                )

    def serialize(self, record: ModuleAtomicResult) -> ModuleSerializedResult:
        timestamps = [
            ("package_install", record.get("timestamp")),
            ("package_last_update", record.get("last_update_time")),
        ]
        timestamps.extend(
            ("package_first_install", user.get("first_install_time"))
            for user in record.get("users", [])
        )
        return [
            {
                "timestamp": timestamp,
                "module": self.__class__.__name__,
                "event": event,
                "data": f"Install or update of package {record['package_name']}",
            }
            for event, timestamp in timestamps
            if timestamp
        ]

    @staticmethod
    def _permission(line: str, permission_type: str) -> dict:
        name, _, details = line.strip().partition(":")
        granted_match = re.search(r"granted=(true|false)", details)
        flags_match = re.search(r"flags=\[\s*([^]]*)\]", details)
        return {
            "name": name,
            "type": permission_type,
            "granted": granted_match.group(1) == "true" if granted_match else None,
            "flags": [
                flag.strip()
                for flag in (flags_match.group(1).split("|") if flags_match else [])
                if flag.strip()
            ],
        }

    @classmethod
    def parse_dumpsys_package_for_details(cls, output: str) -> dict[str, Any]:
        details: dict[str, Any] = {
            "app_id": None,
            "version_name": None,
            "version_code": None,
            "min_sdk": None,
            "target_sdk": None,
            "timestamp": None,
            "last_update_time": None,
            "installer": None,
            "system": False,
            "permissions": [],
            "requested_permissions": [],
            "users": [],
        }
        permission_section: str | None = None
        current_user: dict[str, Any] | None = None
        legacy_first_install: str | None = None

        for line in output.splitlines():
            stripped = line.strip()
            user_match = re.match(r"User (\d+):\s*(.*)", stripped)
            if user_match:
                current_user = {"user_id": int(user_match.group(1)), "permissions": []}
                for key, raw in re.findall(r"(\w+)=([^\s]+)", user_match.group(2)):
                    clean_key = {
                        "notLaunched": "not_launched",
                        "installReason": "install_reason",
                        "uninstallReason": "uninstall_reason",
                        "dataDir": "data_dir",
                    }.get(key, re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower())
                    current_user[clean_key] = _value(raw)
                details["users"].append(current_user)
                permission_section = None
                continue

            header = stripped.lower()
            if header in {
                "declared permissions:",
                "install permissions:",
                "requested permissions:",
                "runtime permissions:",
            }:
                permission_section = header.split()[0]
                continue

            if current_user is not None:
                user_property = re.match(
                    r"(installReason|uninstallReason|dataDir|firstInstallTime)=(.*)",
                    stripped,
                )
                if user_property:
                    key = {
                        "installReason": "install_reason",
                        "uninstallReason": "uninstall_reason",
                        "dataDir": "data_dir",
                        "firstInstallTime": "first_install_time",
                    }[user_property.group(1)]
                    current_user[key] = _value(user_property.group(2))
                    continue

            if permission_section == "requested" and line.startswith("      "):
                details["requested_permissions"].append(stripped)
                continue
            if permission_section in ("declared", "install") and line.startswith(
                "      "
            ):
                details["permissions"].append(
                    cls._permission(stripped, permission_section)
                )
                continue
            if (
                permission_section == "runtime"
                and line.startswith("        ")
                and current_user is not None
            ):
                current_user["permissions"].append(cls._permission(stripped, "runtime"))
                continue

            simple_match = re.match(
                r"(appId|userId|versionName|timeStamp|lastUpdateTime|installerPackageName)=(.*)",
                stripped,
            )
            if simple_match:
                key = {
                    "appId": "app_id",
                    "userId": "app_id",
                    "versionName": "version_name",
                    "timeStamp": "timestamp",
                    "lastUpdateTime": "last_update_time",
                    "installerPackageName": "installer",
                }[simple_match.group(1)]
                raw_value = simple_match.group(2)
                details[key] = (
                    _value(raw_value)
                    if key == "app_id" or raw_value == "null"
                    else raw_value
                )
                continue
            if stripped.startswith("pkgFlags="):
                details["system"] = "SYSTEM" in stripped.split("=", 1)[1].split()
                continue
            version_match = re.match(
                r"versionCode=([^\s]+)(?:\s+minSdk=([^\s]+))?(?:\s+targetSdk=([^\s]+))?",
                stripped,
            )
            if version_match:
                details["version_code"] = _value(version_match.group(1))
                details["min_sdk"] = (
                    _value(version_match.group(2)) if version_match.group(2) else None
                )
                details["target_sdk"] = (
                    _value(version_match.group(3)) if version_match.group(3) else None
                )
            elif stripped.startswith("firstInstallTime="):
                legacy_first_install = stripped.split("=", 1)[1]

        if legacy_first_install:
            user_zero = next(
                (user for user in details["users"] if user["user_id"] == 0), None
            )
            if user_zero is None:
                user_zero = {"user_id": 0, "permissions": []}
                details["users"].append(user_zero)
            user_zero.setdefault("first_install_time", legacy_first_install)
        return details

    def parse(self, content: str) -> None:
        self.results: list[dict[str, Any]] = []
        category: str | None = None
        package: dict[str, Any] | None = None
        block: list[str] = []

        def finish() -> None:
            nonlocal package, block
            if package is not None:
                package.update(self.parse_dumpsys_package_for_details("\n".join(block)))
                self.results.append(package)
            package = None
            block = []

        for line in content.splitlines():
            if line == "Packages:":
                finish()
                category = "active"
                continue
            if line == "Hidden system packages:":
                finish()
                category = "hidden_system"
                continue
            package_match = re.match(r"^  Package \[([^]]+)\]", line)
            if package_match and category:
                finish()
                package = {
                    "package_name": package_match.group(1),
                    "package_type": category,
                }
                continue
            if (
                category
                and line
                and not line.startswith(" ")
                and not line.endswith(" overlay paths:")
            ):
                finish()
                category = None
                continue
            if package is not None:
                block.append(line)
        finish()
