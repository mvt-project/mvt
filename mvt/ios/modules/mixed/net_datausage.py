# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional

from ..net_base import NetBase

DATAUSAGE_BACKUP_IDS = [
    "0d609c54856a9bb2d56729df1d68f2958a88426b",
]
DATAUSAGE_ROOT_PATHS = [
    "private/var/wireless/Library/Databases/DataUsage.sqlite",
]


class Datausage(NetBase):
    """This class extracts data from DataUsage.sqlite and attempts to identify
    any suspicious processes if running on a full filesystem dump.


    """

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
        self._find_ios_database(
            backup_ids=DATAUSAGE_BACKUP_IDS, root_paths=DATAUSAGE_ROOT_PATHS
        )
        self.log.info("Found DataUsage database at path: %s", self.file_path)

        self._extract_net_data()
        self._find_suspicious_processes()
