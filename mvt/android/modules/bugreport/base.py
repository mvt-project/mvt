# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# See the file 'LICENSE' for usage and copying permissions, or find a copy at
#   https://github.com/mvt-project/mvt/blob/main/LICENSE

import fnmatch
import logging
import os
from zipfile import ZipFile

from mvt.common.module import MVTModule

log = logging.getLogger(__name__)


class BugReportModule(MVTModule):
    """This class provides a base for all Android Bug Report modules."""

    zip_archive = None

    def from_folder(self, extract_path: str, extract_files: str) -> None:
        self.extract_path = extract_path
        self.extract_files = extract_files

    def from_zip(self, zip_archive: ZipFile, zip_files: list) -> None:
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
