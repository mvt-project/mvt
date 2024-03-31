# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional

from mvt.android.artifacts.dumpsys_packages import DumpsysPackagesArtifact
from mvt.android.utils import DANGEROUS_PERMISSIONS, DANGEROUS_PERMISSIONS_THRESHOLD

from .base import BugReportModule


class Packages(DumpsysPackagesArtifact, BugReportModule):
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

    def run(self) -> None:
        data = self._get_dumpstate_file()
        if not data:
            self.log.error(
                "Unable to find dumpstate file. "
                "Did you provide a valid bug report archive?"
            )
            return

        data = data.decode("utf-8", errors="replace")
        content = self.extract_dumpsys_section(data, "DUMP OF SERVICE package:")
        self.parse(content)

        for result in self.results:
            dangerous_permissions_count = 0
            for perm in result["permissions"]:
                if perm["name"] in DANGEROUS_PERMISSIONS:
                    dangerous_permissions_count += 1

            if dangerous_permissions_count >= DANGEROUS_PERMISSIONS_THRESHOLD:
                self.log.info(
                    'Found package "%s" requested %d potentially dangerous permissions',
                    result["package_name"],
                    dangerous_permissions_count,
                )

        self.log.info("Extracted details on %d packages", len(self.results))
