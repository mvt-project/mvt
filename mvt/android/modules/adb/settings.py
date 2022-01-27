# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import re
import logging
import os

from .base import AndroidExtraction

log = logging.getLogger(__name__)


class Settings(AndroidExtraction):
    """This module extracts Android system settings."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 serial=None, fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

        self.results = {}

    def run(self):
        self._adb_connect()

        dangerous = [
            {
                "description": "disabled Google Play Protect",
                "key": "package_verifier_enable",
                "value": "-1",
            },
            {
                "description": "disabled Google Play Protect",
                "key": "package_verifier_user_consent",
                "value": "-1",
            },
            {
                "description": "disabled Google Play Protect",
                "key": "upload_apk_enable",
                "value": "0",
            },
            {
                "description": "enabled installation of non-market apps",
                "key": "install_non_market_apps",
                "value": "1",
            },
            {
                "description": "disabled sharing of security reports",
                "key": "send_security_reports",
                "value": "0",
            },
            {
                "description": "disabled sharing of crash logs with manufacturer",
                "key": "samsung_errorlog_agree",
                "value": "0",
            },
            {
                "description": "disabled applications errors reports",
                "key": "send_action_app_error",
                "value": "0",
            },
        ]

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

                for danger in dangerous:
                    if danger["key"] == fields[0] and danger["value"] == fields[1]:
                        self.log.warning("Found suspicious setting \"%s = %s\" (%s)",
                                         fields[0], fields[1], danger["description"])

        self._adb_disconnect()
