# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import fnmatch
import logging
import os
import zipfile
from typing import Any, Dict, List, Optional, Union

from mvt.common.module import MVTModule


class AndroidQFModule(MVTModule):
    """This class provides a base for all Android Data analysis modules."""

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        module_options: Optional[dict] = None,
        log: logging.Logger = logging.getLogger(__name__),
        results: Union[List[Dict[str, Any]], Dict[str, Any], None] = None,
    ) -> None:
        super().__init__(
            file_path=file_path,
            target_path=target_path,
            results_path=results_path,
            module_options=module_options,
            log=log,
            results=results,
        )
        self._path: str = target_path
        self.files: List[str] = []
        self.archive: Optional[zipfile.ZipFile] = None

    def from_folder(self, parent_path: str, files: List[str]):
        self.parent_path = parent_path
        self.files = files

    def from_zip_file(self, archive: zipfile.ZipFile, files: List[str]):
        self.archive = archive
        self.files = files

    def _get_files_by_pattern(self, pattern: str):
        return fnmatch.filter(self.files, pattern)

    def _get_file_content(self, file_path):
        if self.archive:
            handle = self.archive.open(file_path)
        else:
            handle = open(os.path.join(self.parent_path, file_path), "rb")

        data = handle.read()
        handle.close()

        return data
