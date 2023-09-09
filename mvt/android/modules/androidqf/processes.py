# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional

from mvt.android.artifacts.processes import Processes as ProcessesArtifact

from .base import AndroidQFModule


class Processes(ProcessesArtifact, AndroidQFModule):
    """This module analyse running processes"""

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
        ps_files = self._get_files_by_pattern("*/ps.txt")
        if not ps_files:
            return

        self.parse(self._get_file_content(ps_files[0]).decode("utf-8"))
        self.log.info("Identified %d running processes", len(self.results))
