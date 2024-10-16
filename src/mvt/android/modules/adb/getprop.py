# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional

from mvt.android.artifacts.getprop import GetProp as GetPropArtifact

from .base import AndroidExtraction


class Getprop(GetPropArtifact, AndroidExtraction):
    """This module extracts device properties from getprop command."""

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
        output = self._adb_command("getprop")
        self._adb_disconnect()

        self.parse(output)
        self.log.info("Extracted %d Android system properties", len(self.results))
