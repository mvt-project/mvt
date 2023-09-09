# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional

from mvt.android.artifacts.dumpsys_appops import DumpsysAppopsArtifact

from .base import BugReportModule


class Appops(DumpsysAppopsArtifact, BugReportModule):
    """This module extracts information on package from App-Ops Manager."""

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
        content = self._get_dumpstate_file()
        if not content:
            self.log.error(
                "Unable to find dumpstate file. "
                "Did you provide a valid bug report archive?"
            )
            return

        section = self.extract_dumpsys_section(
            content.decode("utf-8", errors="replace"), "DUMP OF SERVICE appops:"
        )
        self.parse(section)

        self.log.info(
            "Identified a total of %d packages in App-Ops Manager", len(self.results)
        )
