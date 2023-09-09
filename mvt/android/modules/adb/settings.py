# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional

from mvt.android.artifacts.settings import Settings as SettingsArtifact

from .base import AndroidExtraction


class Settings(SettingsArtifact, AndroidExtraction):
    """This module extracts Android system settings."""

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        module_options: Optional[dict] = None,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[list] = None,
    ) -> None:
        super().__init__(
            file_path=file_path,
            target_path=target_path,
            results_path=results_path,
            module_options=module_options,
            log=log,
            results=results,
        )

        self.results = {} if not results else results

    def run(self) -> None:
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
