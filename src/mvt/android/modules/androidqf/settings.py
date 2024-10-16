# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional

from mvt.android.artifacts.settings import Settings as SettingsArtifact

from .base import AndroidQFModule


class Settings(SettingsArtifact, AndroidQFModule):
    """This module analyse setting files"""

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
        self.results = {}

    def run(self) -> None:
        for setting_file in self._get_files_by_pattern("*/settings_*.txt"):
            namespace = setting_file[setting_file.rfind("_") + 1 : -4]

            self.results[namespace] = {}
            data = self._get_file_content(setting_file)
            for line in data.decode("utf-8").split("\n"):
                line = line.strip()
                try:
                    key, value = line.split("=", 1)
                except ValueError:
                    continue

                try:
                    self.results[namespace][key] = value
                except IndexError:
                    continue

        self.log.info(
            "Identified %d settings", sum([len(val) for val in self.results.values()])
        )
