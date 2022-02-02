# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import re

from mvt.android.parsers import parse_getprop

from .base import AndroidExtraction

log = logging.getLogger(__name__)


class Getprop(AndroidExtraction):
    """This module extracts device properties from getprop command."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 serial=None, fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

        self.results = {} if not results else results

    def run(self):
        self._adb_connect()
        output = self._adb_command("getprop")
        self._adb_disconnect()

        self.results = parse_getprop(output)

        self.log.info("Extracted %d Android system properties", len(self.results))
