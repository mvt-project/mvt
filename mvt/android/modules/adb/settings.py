# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

from .base import AndroidExtraction

log = logging.getLogger(__name__)


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
]


class Settings(AndroidExtraction):
    """This module extracts Android system settings."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 serial=None, fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

        self.results = {} if not results else results

    def check_indicators(self):
        for namespace, settings in self.results.items():
            for key, value in settings.items():
                for danger in ANDROID_DANGEROUS_SETTINGS:
                    # Check if one of the dangerous settings is using an unsafe
                    # value (different than the one specified).
                    if danger["key"] == key and danger["safe_value"] != value:
                        self.log.warning("Found suspicious setting \"%s = %s\" (%s)",
                                         key, value, danger["description"])
                        break

    def run(self):
        self._adb_connect()

        for namespace in ["system", "secure", "global"]:
            out = self._adb_command(f"cmd settings list {namespace}")
            if not out:
                continue

            self.results[namespace] = {}

            for line in out.splitlines():
                line = line.strip()
                if line == "":
                    continue

                fields = line.split("=", 1)
                try:
                    self.results[namespace][fields[0]] = fields[1]
                except IndexError:
                    continue

        self._adb_disconnect()
