# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional

from mvt.android.artifacts.dumpsys_accessibility import DumpsysAccessibilityArtifact

from .base import AndroidExtraction


class DumpsysAccessibility(DumpsysAccessibilityArtifact, AndroidExtraction):
    """This module extracts stats on accessibility."""

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

    def run(self) -> None:
        self._adb_connect()
        output = self._adb_command("dumpsys accessibility")
        self._adb_disconnect()

        self.parse(output)

        for result in self.results:
            self.log.info(
                'Found installed accessibility service "%s"', result.get("service")
            )

        self.log.info(
            "Identified a total of %d accessibility services", len(self.results)
        )
