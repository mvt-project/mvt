# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional

from mvt.android.artifacts.dumpsys_adb import DumpsysADBArtifact

from .base import AndroidQFModule


class DumpsysADBState(DumpsysADBArtifact, AndroidQFModule):
    """This module extracts ADB keystore state."""

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
        dumpsys_file = self._get_files_by_pattern("*/dumpsys.txt")
        if not dumpsys_file:
            return

        full_dumpsys = self._get_file_content(dumpsys_file[0])
        content = self.extract_dumpsys_section(
            full_dumpsys,
            b"DUMP OF SERVICE adb:",
            binary=True,
        )
        self.parse(content)
        if self.results:
            self.log.info(
                "Identified a total of %d trusted ADB keys",
                len(self.results[0].get("user_keys", [])),
            )
