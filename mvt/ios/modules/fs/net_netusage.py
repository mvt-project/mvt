# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import sqlite3

from ..net_base import NetBase

NETUSAGE_ROOT_PATHS = [
    "private/var/networkd/netusage.sqlite",
    "private/var/networkd/db/netusage.sqlite"
]


class Netusage(NetBase):
    """This class extracts data from netusage.sqlite and attempts to identify
    any suspicious processes if running on a full filesystem dump.


    """

    def __init__(self, file_path: str = None, target_path: str = None,
                 results_path: str = None, fast_mode: bool = False,
                 log: logging.Logger = None, results: list = []) -> None:
        super().__init__(file_path=file_path, target_path=target_path,
                         results_path=results_path, fast_mode=fast_mode,
                         log=log, results=results)

    def run(self) -> None:
        for netusage_path in self._get_fs_files_from_patterns(NETUSAGE_ROOT_PATHS):
            self.file_path = netusage_path
            self.log.info("Found NetUsage database at path: %s", self.file_path)
            try:
                self._extract_net_data()
            except sqlite3.OperationalError as e:
                self.log.info("Skipping this NetUsage database because it seems empty or malformed: %s", e)
                continue

        self._find_suspicious_processes()
