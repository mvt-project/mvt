# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import fnmatch
import logging
import os
from tarfile import TarFile
from typing import List, Optional

from mvt.common.module import MVTModule


class BackupExtraction(MVTModule):
    """This class provides a base for all backup extractios modules"""

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
        self.ab = None
        self.backup_path = None
        self.tar = None
        self.files = []

    def from_folder(self, backup_path: Optional[str], files: List[str]) -> None:
        """
        Get all the files and list them
        """
        self.backup_path = backup_path
        self.files = files

    def from_ab(
        self, file_path: Optional[str], tar: Optional[TarFile], files: List[str]
    ) -> None:
        """
        Extract the files
        """
        self.ab = file_path
        self.tar = tar
        self.files = files

    def _get_files_by_pattern(self, pattern: str) -> list:
        return fnmatch.filter(self.files, pattern)

    def _get_file_content(self, file_path: str) -> bytes:
        if self.ab:
            try:
                member = self.tar.getmember(file_path)
            except KeyError:
                return None
            handle = self.tar.extractfile(member)
        else:
            handle = open(os.path.join(self.backup_path, file_path), "rb")

        data = handle.read()
        handle.close()

        return data
