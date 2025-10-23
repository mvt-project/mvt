# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import json
from typing import Optional

from mvt.android.artifacts.mounts import Mounts as MountsArtifact

from .base import AndroidQFModule


class Mounts(MountsArtifact, AndroidQFModule):
    """This module extracts and analyzes mount information from AndroidQF acquisitions."""

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
        self.results = []

    def run(self) -> None:
        """
        Run the mounts analysis module.

        This module looks for mount information files collected by androidqf
        and analyzes them for suspicious configurations, particularly focusing
        on detecting root access indicators like /system mounted as read-write.
        """
        mount_files = self._get_files_by_pattern("*/mounts.json")

        if not mount_files:
            self.log.info("No mount information file found")
            return

        self.log.info("Found mount information file: %s", mount_files[0])

        try:
            data = self._get_file_content(mount_files[0]).decode(
                "utf-8", errors="replace"
            )
        except Exception as exc:
            self.log.error("Failed to read mount information file: %s", exc)
            return

        # Parse the mount data
        try:
            json_data = json.loads(data)

            if isinstance(json_data, list):
                # AndroidQF format: array of strings like
                # "/dev/block/dm-12 on / type ext4 (ro,seclabel,noatime)"
                mount_content = "\n".join(json_data)
            self.parse(mount_content)
        except Exception as exc:
            self.log.error("Failed to parse mount information: %s", exc)
            return

        self.log.info("Extracted a total of %d mount entries", len(self.results))
