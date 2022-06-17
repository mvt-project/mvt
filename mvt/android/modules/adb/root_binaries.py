# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

from .base import AndroidExtraction

log = logging.getLogger(__name__)


class RootBinaries(AndroidExtraction):
    """This module extracts the list of installed packages."""

    def __init__(self, file_path: str = None, target_path: str = None,
                 results_path: str = None, fast_mode: bool = False,
                 log: logging.Logger = None, results: list = []) -> None:
        super().__init__(file_path=file_path, target_path=target_path,
                         results_path=results_path, fast_mode=fast_mode,
                         log=log, results=results)

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

            self.detected.append(root_binary)
            self.log.warning("Found root binary \"%s\"", root_binary)

        self._adb_disconnect()
