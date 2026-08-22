# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import re

from .artifact import AndroidArtifact

ANDROID_DANGEROUS_SETTINGS = [
    {
        "description": "disabled Google Play Services apps verification",
        "key": "verifier_verify_adb_installs",
        "safe_value": "1",
    },
    {
        "description": "disabled Google Play Protect",
        "key": "package_verifier_enable",
        "safe_value": "1",
    },
    {
        "description": "disabled APK package verification",
        "key": "package_verifier_state",
        "safe_value": "1",
    },
    {
        "description": "disabled Google Play Protect",
        "key": "package_verifier_user_consent",
        "safe_value": "1",
    },
    {
        "description": "disabled Google Play Protect",
        "key": "upload_apk_enable",
        "safe_value": "1",
    },
    {
        "description": "disabled confirmation of adb apps installation",
        "key": "adb_install_need_confirm",
        "safe_value": "1",
    },
    {
        "description": "disabled sharing of security reports",
        "key": "send_security_reports",
        "safe_value": "1",
    },
    {
        "description": "disabled sharing of crash logs with manufacturer",
        "key": "samsung_errorlog_agree",
        "safe_value": "1",
    },
    {
        "description": "disabled applications errors reports",
        "key": "send_action_app_error",
        "safe_value": "1",
    },
    {
        "description": "enabled accessibility services",
        "key": "accessibility_enabled",
        "safe_value": "0",
    },
]


class Settings(AndroidArtifact):
    def parse(self, content: str) -> None:
        self.results: dict[str, dict[str, str]] = {}
        namespace: str | None = None
        for line in content.splitlines():
            heading = re.match(
                r"^(CONFIG|GLOBAL|SECURE|SYSTEM) SETTINGS \(user (\d+)\)$",
                line.strip(),
            )
            if heading:
                namespace = f"{heading.group(1).lower()}:user_{heading.group(2)}"
                self.results[namespace] = {}
                continue
            if namespace is None or not line.startswith("_id:"):
                continue
            setting = re.match(
                r"^_id:\S+\s+name:(.*?)\s+pkg:.*?\s+value:(.*?)"
                r"(?:\s+default:.*\s+defaultSystemSet:(?:true|false))?$",
                line,
            )
            if setting:
                self.results[namespace][setting.group(1)] = setting.group(2)

    def check_indicators(self) -> None:
        for namespace, settings in self.results.items():
            for key, value in settings.items():
                for danger in ANDROID_DANGEROUS_SETTINGS:
                    # Check if one of the dangerous settings is using an unsafe
                    # value (different than the one specified).
                    if danger["key"] == key and danger["safe_value"] != value:
                        self.alertstore.medium(
                            f'Found suspicious "{namespace}" setting "{key} = {value}" ({danger["description"]})',
                            "",
                            {
                                "namespace": namespace,
                                "key": key,
                                "value": value,
                                "description": danger["description"],
                            },
                        )
                        break
