# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional

from .base import AndroidExtraction


class RootBinaries(AndroidExtraction):
    """This module extracts the list of installed packages."""

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

    def check_indicators(self) -> None:
        for root_binary in self.results:
            self.detected.append(root_binary)
            self.log.warning('Found root binary "%s"', root_binary)

    def run(self) -> None:
        root_binaries = [
            "su",
            "busybox",
            "supersu",
            "Superuser.apk",
            "KingoUser.apk",
            "SuperSu.apk",
            "magisk",
            "magiskhide",
            "magiskinit",
            "magiskpolicy",
        ]

        self._adb_connect()

        for root_binary in root_binaries:
            root_binary = root_binary.strip()
            if not root_binary:
                continue

            output = self._adb_command(f"which -a {root_binary}")
            output = output.strip()

            if not output:
                continue

            if "which: not found" in output:
                continue

            self.results.append(root_binary)

        self._adb_disconnect()
