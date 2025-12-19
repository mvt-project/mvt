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
from mvt.common.indicators import Indicators

from .modules.bugreport import BUGREPORT_MODULES

log = logging.getLogger(__name__)


class CmdAndroidCheckBugreport(Command):
    def __init__(
        self,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        ioc_files: Optional[list] = None,
        iocs: Optional[Indicators] = None,
        module_name: Optional[str] = None,
        serial: Optional[str] = None,
        module_options: Optional[dict] = None,
        hashes: Optional[bool] = False,
        sub_command: Optional[bool] = False,
        disable_version_check: bool = False,
        disable_indicator_check: bool = False,
    ) -> None:
        super().__init__(
            target_path=target_path,
            results_path=results_path,
            ioc_files=ioc_files,
            iocs=iocs,
            module_name=module_name,
            serial=serial,
            module_options=module_options,
            hashes=hashes,
            sub_command=sub_command,
            log=log,
            disable_version_check=disable_version_check,
            disable_indicator_check=disable_indicator_check,
        )

        self.name = "check-bugreport"
        self.modules = BUGREPORT_MODULES

        self.__format: str = ""
        self.__zip: Optional[ZipFile] = None
        self.__files: List[str] = []

    def from_dir(self, dir_path: str) -> None:
        """This method is used to initialize the bug report analysis from an
        uncompressed directory.
        """
        self.__format = "dir"
        self.target_path = dir_path
        parent_path = Path(dir_path).absolute().as_posix()
        for root, _, subfiles in os.walk(os.path.abspath(dir_path)):
            for file_name in subfiles:
                file_path = os.path.relpath(os.path.join(root, file_name), parent_path)
                self.__files.append(file_path)

    def from_zip(self, bugreport_zip: ZipFile) -> None:
        """This method is used to initialize the bug report analysis from a
        compressed archive.
        """
        # NOTE: This will be invoked either by the CLI directly,or by the
        # check-androidqf command. We need this because we want to support
        # check-androidqf to analyse compressed archives itself too.
        # So, we'll need to extract bugreport.zip from a 'androidqf.zip', and
        # since nothing is written on disk, we need to be able to pass this
        # command a ZipFile instance in memory.

        self.__format = "zip"
        self.__zip = bugreport_zip
        for file_name in self.__zip.namelist():
            self.__files.append(file_name)

    def init(self) -> None:
        if not self.target_path:
            return

        if os.path.isfile(self.target_path):
            self.from_zip(ZipFile(self.target_path))
        elif os.path.isdir(self.target_path):
            self.from_dir(self.target_path)

    def module_init(self, module: BugReportModule) -> None:  # type: ignore[override]
        if self.__format == "zip":
            module.from_zip(self.__zip, self.__files)
        else:
            module.from_dir(self.target_path, self.__files)

    def finish(self) -> None:
        if self.__zip:
            self.__zip.close()
