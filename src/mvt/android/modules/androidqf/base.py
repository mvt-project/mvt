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
        self.parent_path = None
        self._path: str = target_path
        self.files: List[str] = []
        self.archive: Optional[zipfile.ZipFile] = None

    def from_dir(self, parent_path: str, files: List[str]) -> None:
        self.parent_path = parent_path
        self.files = files

    def from_zip(self, archive: zipfile.ZipFile, files: List[str]) -> None:
        self.archive = archive
        self.files = files

    def _get_files_by_pattern(self, pattern: str):
        return fnmatch.filter(self.files, pattern)

    def _get_device_timezone(self):
        """
        Get the device timezone from the getprop.txt file.

        This is needed to map local timestamps stored in some
        Android log files to UTC/timezone-aware timestamps.
        """
        get_prop_files = self._get_files_by_pattern("*/getprop.txt")
        if not get_prop_files:
            self.log.warning(
                "Could not find getprop.txt file. "
                "Some timestamps and timeline data may be incorrect."
            )
            return None

        from mvt.android.artifacts.getprop import GetProp

        properties_artifact = GetProp()
        prop_data = self._get_file_content(get_prop_files[0]).decode("utf-8")
        properties_artifact.parse(prop_data)
        timezone = properties_artifact.get_device_timezone()
        if timezone:
            self.log.debug("Identified local phone timezone: %s", timezone)
            return timezone

        self.log.warning(
            "Could not find or determine local device timezone. "
            "Some timestamps and timeline data may be incorrect."
        )
        return None

    def _get_file_content(self, file_path):
        if self.archive:
            handle = self.archive.open(file_path)
        else:
            handle = open(os.path.join(self.parent_path, file_path), "rb")

        data = handle.read()
        handle.close()

        return data
