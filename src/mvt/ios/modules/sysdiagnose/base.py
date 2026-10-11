# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import fnmatch
import logging
import os
import re
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from mvt.common.module import MVTModule, ModuleResults


class SysdiagnoseExtraction(MVTModule):
    """Base class for custom modules that analyze an iOS sysdiagnose."""

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        module_options: Optional[dict] = None,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[ModuleResults] = None,
    ) -> None:
        super().__init__(
            file_path=file_path,
            target_path=target_path,
            results_path=results_path,
            module_options=module_options,
            log=log,
            results=results,
        )
        self.parent_path: Optional[str] = None
        self.files: list[str] = []
        self.tar: Optional[tarfile.TarFile] = None
        self.tar_files: list[str] = []
        self.ips_files: list[dict[str, object]] = []

    def from_sysdiagnose_folder(
        self, target_path: str, sysdiagnose_files: list[str]
    ) -> None:
        self.parent_path = Path(target_path).absolute().parent.as_posix()
        self.files = sysdiagnose_files

    def from_sysdiagnose_tar(
        self, sysdiagnose_archive: tarfile.TarFile, sysdiagnose_files: list[str]
    ) -> None:
        self.tar = sysdiagnose_archive
        self.tar_files = sysdiagnose_files

    def _extract_timezone(self):
        """Determine the sysdiagnose timezone from its diagnostic log."""
        file_paths = self._get_files_by_pattern("*/sysdiagnose.log")
        if not file_paths:
            self.log.info(
                "Unable to determine the timezone in which the sysdiagnose was "
                "generated. Assuming UTC for logs without a timezone."
            )
            return timezone.utc

        content = self._get_file_content(file_paths[0]).decode(
            "utf-8", errors="replace"
        )
        filenames = re.findall(r"sysdiagnose_\S+?\.tar\.gz", content)
        if not filenames:
            self.log.info(
                "Unable to determine the timezone in which the sysdiagnose was "
                "generated. Assuming UTC for logs without a timezone."
            )
            return timezone.utc

        timestamp = "_".join(
            filenames[0].removesuffix(".tar.gz").split("_")[1:3]
        )
        sysdiagnose_timezone = datetime.strptime(
            timestamp, "%Y.%m.%d_%H-%M-%S%z"
        ).tzinfo
        self.log.info(
            "Based on the sysdiagnose filename, assuming timezone %s for logs "
            "without a timezone.",
            sysdiagnose_timezone,
        )
        return sysdiagnose_timezone

    def _get_files_by_pattern(self, pattern: str) -> list[str]:
        file_names = self.tar_files if self.tar else self.files
        return fnmatch.filter(file_names, pattern)

    def _get_file_content(self, file_path: str) -> bytes:
        if self.tar:
            handle = self.tar.extractfile(self.tar.getmember(file_path))
        else:
            if self.parent_path is None:
                raise RuntimeError("Sysdiagnose folder has not been initialized")
            handle = open(os.path.join(self.parent_path, file_path), "rb")

        if handle is None:
            return b""
        with handle:
            return handle.read()
