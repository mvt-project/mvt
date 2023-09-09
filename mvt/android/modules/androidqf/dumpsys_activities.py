# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional

from mvt.android.artifacts.dumpsys_package_activities import (
    DumpsysPackageActivitiesArtifact,
)

from .base import AndroidQFModule


class DumpsysActivities(DumpsysPackageActivitiesArtifact, AndroidQFModule):
    """This module extracts details on receivers for risky activities."""

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

        self.results = results if results else []

    def run(self) -> None:
        dumpsys_file = self._get_files_by_pattern("*/dumpsys.txt")
        if not dumpsys_file:
            return

        # Get data and extract the dumpsys section
        data = self._get_file_content(dumpsys_file[0]).decode("utf-8", errors="replace")
        content = self.extract_dumpsys_section(data, "DUMP OF SERVICE package:")
        # Parse it
        self.parse(content)

        self.log.info("Extracted %d package activities", len(self.results))
