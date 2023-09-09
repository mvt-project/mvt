# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# See the file 'LICENSE' for usage and copying permissions, or find a copy at
#   https://github.com/mvt-project/mvt/blob/main/LICENSE

import fnmatch
import logging
import os
from typing import List, Optional
from zipfile import ZipFile

from mvt.common.module import MVTModule


class BugReportModule(MVTModule):
    """This class provides a base for all Android Bug Report modules."""

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

        self.zip_archive: Optional[ZipFile] = None
        self.extract_path: Optional[str] = None
        self.extract_files: List[str] = []
        self.zip_files: List[str] = []

    def from_folder(
        self, extract_path: Optional[str], extract_files: List[str]
    ) -> None:
        self.extract_path = extract_path
        self.extract_files = extract_files

    def from_zip(self, zip_archive: Optional[ZipFile], zip_files: List[str]) -> None:
        self.zip_archive = zip_archive
        self.zip_files = zip_files

    def _get_files_by_pattern(self, pattern: str) -> list:
        file_names = []
        if self.zip_archive:
            for zip_file in self.zip_files:
                file_names.append(zip_file)
        else:
            file_names = self.extract_files

        return fnmatch.filter(file_names, pattern)

    def _get_files_by_patterns(self, patterns: list) -> list:
        for pattern in patterns:
            matches = self._get_files_by_pattern(pattern)
            if matches:
                return matches

        return []

    def _get_file_content(self, file_path: str) -> bytes:
        if self.zip_archive:
            handle = self.zip_archive.open(file_path)
        else:
            handle = open(os.path.join(self.extract_path, file_path), "rb")

        data = handle.read()
        handle.close()

        return data

    def _get_dumpstate_file(self) -> bytes:
        main = self._get_files_by_pattern("main_entry.txt")
        if main:
            main_content = self._get_file_content(main[0])
            try:
                return self._get_file_content(main_content.decode().strip())
            except KeyError:
                return None
        else:
            dumpstate_logs = self._get_files_by_pattern("dumpState_*.log")
            if not dumpstate_logs:
                return None

            return self._get_file_content(dumpstate_logs[0])

        return None
