# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os

import pkg_resources

from .base import AndroidExtraction

log = logging.getLogger(__name__)


class RootBinaries(AndroidExtraction):
    """This module extracts the list of installed packages."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 serial=None, fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def run(self):
        root_binaries_path = os.path.join("..", "..", "data", "root_binaries.txt")
        root_binaries_string = pkg_resources.resource_string(__name__, root_binaries_path)
        root_binaries = root_binaries_string.decode("utf-8").splitlines()

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
