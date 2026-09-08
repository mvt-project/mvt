# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
from pathlib import Path
from typing import List, Optional
from zipfile import ZipFile

from mvt.android.artifacts.getprop import GetProp
from mvt.android.modules.bugreport.base import BugReportModule
from mvt.common.command import Command
from mvt.common.indicators import Indicators
from mvt.common.module import MVTModule

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
        custom_modules: Optional[list[type[MVTModule]]] = None,
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
            custom_modules=custom_modules,
        )

        self.platform = "android"
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
        if self.target_path:
            self.log.info("Checking Android bug report at path: %s", self.target_path)
            if os.path.isfile(self.target_path):
                self.from_zip(ZipFile(self.target_path))
            elif os.path.isdir(self.target_path):
                self.from_dir(self.target_path)
                self.log.warning(
                    "Analysing an unpacked bugreport: file timestamps come from "
                    "the extraction, not from the device. Analyse the original "
                    "zip to keep the device's file timestamps."
                )
        if self.__format:
            self._resolve_device_timezone()

    def _resolve_device_timezone(self) -> None:
        """Name the device's timezone in module_options unless it is known already.

        A bugreport's SYSTEM PROPERTIES section carries persist.sys.timezone.
        Zip entry times are the device's wall clock, and modules read them in
        this zone; --timezone or check-androidqf's own reading takes precedence.
        """
        if self.module_options.get("device_timezone"):
            self.log.info("Device timezone: %s", self.module_options["device_timezone"])
            return

        probe = BugReportModule(log=self.log)
        self.module_init(probe)
        timezone = None
        try:
            dumpstate = probe._get_dumpstate_file()
        except Exception as exc:
            self.log.warning("Could not read the bugreport's dumpstate: %s", exc)
            dumpstate = None
        if dumpstate:
            properties = GetProp()
            properties.parse(
                BugReportModule.extract_command_section(
                    dumpstate.decode("utf-8", errors="replace"),
                    "------ SYSTEM PROPERTIES",
                )
            )
            timezone = properties.get_device_timezone()
        if timezone:
            self.log.info("Device timezone identified from the bugreport: %s", timezone)
            self.module_options["device_timezone"] = timezone
        else:
            self.log.warning(
                "persist.sys.timezone not found in the bugreport; file timestamps "
                "are the device's wall clock without a timezone. Pass --timezone "
                "to name it."
            )

    def module_init(self, module: BugReportModule) -> None:  # type: ignore[override]
        if self.__format == "zip":
            module.from_zip(self.__zip, self.__files)
        else:
            if not self.target_path:
                raise ValueError("target_path is not set")
            module.from_dir(self.target_path, self.__files)

    def finish(self) -> None:
        if self.__zip:
            self.__zip.close()
