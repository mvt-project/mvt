# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
from pathlib import Path
from typing import List, Optional
from zipfile import ZipFile

from mvt.android.modules.bugreport.base import BugReportModule
from mvt.common.command import Command

from .modules.bugreport import BUGREPORT_MODULES

log = logging.getLogger(__name__)


class CmdAndroidCheckBugreport(Command):
    def __init__(
        self,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        ioc_files: Optional[list] = None,
        module_name: Optional[str] = None,
        serial: Optional[str] = None,
        module_options: Optional[dict] = None,
        hashes: bool = False,
    ) -> None:
        super().__init__(
            target_path=target_path,
            results_path=results_path,
            ioc_files=ioc_files,
            module_name=module_name,
            serial=serial,
            module_options=module_options,
            hashes=hashes,
            log=log,
        )

        self.name = "check-bugreport"
        self.modules = BUGREPORT_MODULES

        self.bugreport_format: str = ""
        self.bugreport_archive: Optional[ZipFile] = None
        self.bugreport_files: List[str] = []

    def init(self) -> None:
        if not self.target_path:
            return

        if os.path.isfile(self.target_path):
            self.bugreport_format = "zip"
            self.bugreport_archive = ZipFile(self.target_path)
            for file_name in self.bugreport_archive.namelist():
                self.bugreport_files.append(file_name)
        elif os.path.isdir(self.target_path):
            self.bugreport_format = "dir"
            parent_path = Path(self.target_path).absolute().as_posix()
            for root, _, subfiles in os.walk(os.path.abspath(self.target_path)):
                for file_name in subfiles:
                    file_path = os.path.relpath(
                        os.path.join(root, file_name), parent_path
                    )
                    self.bugreport_files.append(file_path)

    def module_init(self, module: BugReportModule) -> None:  # type: ignore[override]
        if self.bugreport_format == "zip":
            module.from_zip(self.bugreport_archive, self.bugreport_files)
        else:
            module.from_folder(self.target_path, self.bugreport_files)

    def finish(self) -> None:
        if self.bugreport_archive:
            self.bugreport_archive.close()
