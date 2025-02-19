# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import os
import datetime
import logging
from typing import Optional

from mvt.common.utils import convert_datetime_to_iso
from mvt.common.module_types import ModuleResults
from .base import AndroidQFModule
from mvt.android.artifacts.file_timestamps import FileTimestampsArtifact


class AQFLogTimestamps(FileTimestampsArtifact, AndroidQFModule):
    """This module creates timeline for log files extracted by AQF."""

    slug = "aqf_log_timestamps"

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        module_options: Optional[dict] = None,
        log: logging.Logger = logging.getLogger(__name__),
        results: ModuleResults = [],
    ) -> None:
        super().__init__(
            file_path=file_path,
            target_path=target_path,
            results_path=results_path,
            module_options=module_options,
            log=log,
            results=results,
        )

    def _get_file_modification_time(self, file_path: str) -> dict:
        if self.archive:
            file_timetuple = self.archive.getinfo(file_path).date_time
            return datetime.datetime(*file_timetuple)
        else:
            file_stat = os.stat(os.path.join(self.parent_path, file_path))
            return datetime.datetime.fromtimestamp(file_stat.st_mtime)

    def run(self) -> None:
        filesystem_files = self._get_files_by_pattern("*/logs/*")

        self.results = []
        for file in filesystem_files:
            # Only the modification time is available in the zip file metadata.
            # The timezone is the local timezone of the machine the phone.
            modification_time = self._get_file_modification_time(file)
            self.results.append(
                {
                    "path": file,
                    "modified_time": convert_datetime_to_iso(modification_time),
                }
            )

        self.log.info(
            "Extracted a total of %d filesystem timestamps from AndroidQF logs directory.",
            len(self.results),
        )
