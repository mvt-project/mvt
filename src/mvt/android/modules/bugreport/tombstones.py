# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional

from mvt.android.artifacts.tombstone_crashes import TombstoneCrashArtifact
from mvt.common.module_types import ModuleResults
from .base import BugReportModule


class Tombstones(TombstoneCrashArtifact, BugReportModule):
    """This module extracts records from battery daily updates."""

    slug = "tombstones"

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

    def run(self) -> None:
        tombstone_files = self._get_files_by_pattern("*/tombstone_*")
        if not tombstone_files:
            self.log.error(
                "Unable to find any tombstone files. "
                "Did you provide a valid bugreport archive?"
            )
            return

        for tombstone_file in sorted(tombstone_files):
            tombstone_filename = tombstone_file.split("/")[-1]
            modification_time = self._get_file_modification_time(tombstone_file)
            tombstone_data = self._get_file_content(tombstone_file)

            try:
                if tombstone_file.endswith(".pb"):
                    self.parse_protobuf(
                        tombstone_filename, modification_time, tombstone_data
                    )
                else:
                    self.parse(tombstone_filename, modification_time, tombstone_data)
            except ValueError as e:
                # Catch any exceptions raised during parsing or validation.
                self.log.error(f"Error parsing tombstone file {tombstone_file}: {e}")

        self.log.info(
            "Extracted a total of %d tombstone files",
            len(self.results),
        )
