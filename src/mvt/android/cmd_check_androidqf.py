# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import List, Optional

from mvt.android.artifacts.getprop import GetProp
from mvt.android.cmd_check_intrusion_logs import CmdAndroidCheckIntrusionLogs
from mvt.android.cmd_check_backup import CmdAndroidCheckBackup
from mvt.android.cmd_check_bugreport import CmdAndroidCheckBugreport
from mvt.common.command import Command
from mvt.common.indicators import Indicators

from .modules.androidqf import ANDROIDQF_MODULES
from .modules.androidqf.base import AndroidQFModule

log = logging.getLogger(__name__)


class NoAndroidQFTargetPath(Exception):
    pass


class NoAndroidQFBugReport(Exception):
    pass


class NoAndroidQFBackup(Exception):
    pass


class CmdAndroidCheckAndroidQF(Command):
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

        self.name = "check-androidqf"
        self.modules = ANDROIDQF_MODULES

        self.__format: Optional[str] = None
        self.__zip: Optional[zipfile.ZipFile] = None
        self.__files: List[str] = []

    def init(self):
        if not self.target_path:
            raise NoAndroidQFTargetPath

        if os.path.isdir(self.target_path):
            self.__format = "dir"
            parent_path = Path(self.target_path).absolute().parent.as_posix()
            target_abs_path = os.path.abspath(self.target_path)
            for root, subdirs, subfiles in os.walk(target_abs_path):
                for fname in subfiles:
                    file_path = os.path.relpath(os.path.join(root, fname), parent_path)
                    self.__files.append(file_path)
        elif os.path.isfile(self.target_path):
            self.__format = "zip"
            self.__zip = zipfile.ZipFile(self.target_path)
            self.__files = self.__zip.namelist()

    def module_init(self, module: AndroidQFModule) -> None:  # type: ignore[override]
        if self.__format == "zip" and self.__zip:
            module.from_zip(self.__zip, self.__files)
            return

        if not self.target_path:
            raise NoAndroidQFTargetPath

        parent_path = Path(self.target_path).absolute().parent.as_posix()
        module.from_dir(parent_path, self.__files)

    def load_bugreport(self) -> zipfile.ZipFile:
        bugreport_zip_path = None
        for file_name in self.__files:
            if file_name.endswith("bugreport.zip"):
                bugreport_zip_path = file_name
                break
        else:
            raise NoAndroidQFBugReport

        if self.__format == "zip" and self.__zip:
            handle = self.__zip.open(bugreport_zip_path)
            return zipfile.ZipFile(handle)

        if self.__format == "dir" and self.target_path:
            parent_path = Path(self.target_path).absolute().parent.as_posix()
            bug_report_path = os.path.join(parent_path, bugreport_zip_path)
            return zipfile.ZipFile(bug_report_path)

        raise NoAndroidQFBugReport

    def load_backup(self) -> bytes:
        backup_ab_path = None
        for file_name in self.__files:
            if file_name.endswith("backup.ab"):
                backup_ab_path = file_name
                break
        else:
            raise NoAndroidQFBackup

        if self.__format == "zip" and self.__zip:
            backup_file_handle = self.__zip.open(backup_ab_path)
            return backup_file_handle.read()

        if self.__format == "dir" and self.target_path:
            parent_path = Path(self.target_path).absolute().parent.as_posix()
            backup_path = os.path.join(parent_path, backup_ab_path)
            with open(backup_path, "rb") as backup_file:
                backup_ab_data = backup_file.read()
            return backup_ab_data

        raise NoAndroidQFBackup

    def _read_device_timezone(self) -> Optional[str]:
        getprop_files = [
            f for f in self.__files if f.replace("\\", "/").endswith("getprop.txt")
        ]
        if not getprop_files:
            self.log.warning(
                "Could not find getprop.txt; intrusion log timestamps will use UTC."
            )
            return None

        try:
            content = self._get_file_content(getprop_files[0]).decode(
                "utf-8", errors="ignore"
            )
        except Exception as exc:
            self.log.warning("Could not read getprop.txt: %s", exc)
            return None

        props = GetProp()
        props.parse(content)
        timezone = props.get_device_timezone()
        if timezone:
            self.log.info(
                "Device timezone identified from getprop.txt: %s",
                timezone,
            )
        else:
            self.log.warning(
                "persist.sys.timezone not found in getprop.txt; "
                "intrusion log timestamps will use UTC."
            )

        return timezone

    def _get_file_content(self, file_path: str) -> bytes:
        if self.__format == "zip" and self.__zip:
            handle = self.__zip.open(file_path)
            try:
                return handle.read()
            finally:
                handle.close()

        if self.__format == "dir" and self.target_path:
            parent_path = Path(self.target_path).absolute().parent.as_posix()
            with open(os.path.join(parent_path, file_path), "rb") as handle:
                return handle.read()

        raise FileNotFoundError(file_path)

    def run_bugreport_cmd(self) -> bool:
        bugreport = None
        try:
            bugreport = self.load_bugreport()
        except NoAndroidQFBugReport:
            self.log.warning(
                "Skipping bugreport modules as no bugreport.zip found in AndroidQF data."
            )
            return False
        else:
            cmd = CmdAndroidCheckBugreport(
                target_path=None,
                results_path=self.results_path,
                ioc_files=self.ioc_files,
                iocs=self.iocs,
                module_options=self.module_options,
                hashes=self.hashes,
                sub_command=True,
            )
            cmd.from_zip(bugreport)
            cmd.run()

            self.timeline.extend(cmd.timeline)
            self.alertstore.extend(cmd.alertstore.alerts)
        finally:
            if bugreport:
                bugreport.close()

        return True

    def run_backup_cmd(self) -> bool:
        try:
            backup = self.load_backup()
        except NoAndroidQFBackup:
            self.log.warning(
                "Skipping backup modules as no backup.ab found in AndroidQF data."
            )
            return False

        cmd = CmdAndroidCheckBackup(
            target_path=None,
            results_path=self.results_path,
            ioc_files=self.ioc_files,
            iocs=self.iocs,
            module_options=self.module_options,
            hashes=self.hashes,
            sub_command=True,
        )
        cmd.from_ab(backup)
        cmd.run()

        self.timeline.extend(cmd.timeline)
        self.alertstore.extend(cmd.alertstore.alerts)
        return True

    def run_intrusion_logs_cmd(self) -> bool:
        intrusion_log_files = [
            f
            for f in self.__files
            if "/intrusion_logs/" in f.replace("\\", "/")
            or f.replace("\\", "/").startswith("intrusion_logs/")
        ]

        if not intrusion_log_files:
            self.log.info(
                "No intrusion_logs folder found in AndroidQF data, "
                "skipping intrusion logs analysis."
            )
            return False

        self.log.info(
            "Found intrusion_logs folder in AndroidQF data, running intrusion logs analysis."
        )

        intrusion_logs_path = None
        temp_dir = None

        try:
            if self.__format == "dir" and self.target_path:
                intrusion_logs_path = os.path.join(
                    os.path.abspath(self.target_path), "intrusion_logs"
                )
                if not os.path.isdir(intrusion_logs_path):
                    self.log.warning(
                        "intrusion_logs directory not found at %s",
                        intrusion_logs_path,
                    )
                    return False

            elif self.__format == "zip" and self.__zip:
                temp_dir = tempfile.mkdtemp(prefix="mvt_intrusion_logs_")
                for entry in intrusion_log_files:
                    normalized = entry.replace("\\", "/")
                    idx = normalized.find("intrusion_logs/")
                    relative = normalized[idx + len("intrusion_logs/") :]
                    if not relative or relative.endswith("/"):
                        continue

                    target = os.path.join(temp_dir, relative)
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with self.__zip.open(entry) as src, open(target, "wb") as dst:
                        dst.write(src.read())

                intrusion_logs_path = temp_dir
            else:
                return False

            adv_module_options = dict(self.module_options or {})
            if device_timezone := self._read_device_timezone():
                adv_module_options["device_timezone"] = device_timezone

            cmd = CmdAndroidCheckIntrusionLogs(
                target_path=intrusion_logs_path,
                results_path=self.results_path,
                ioc_files=self.ioc_files,
                iocs=self.iocs,
                module_options=adv_module_options,
                hashes=self.hashes,
                sub_command=True,
            )
            cmd.run()

            self.timeline.extend(cmd.timeline)
            self.alertstore.extend(cmd.alertstore.alerts)
            return True

        finally:
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)

    def finish(self) -> None:
        """
        Run nested modules if their respective files are found in AndroidQF data.
        """
        self.run_bugreport_cmd()
        self.run_backup_cmd()
        self.run_intrusion_logs_cmd()
