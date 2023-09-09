# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import io
import logging
import os
import sys
import tarfile
from pathlib import Path
from typing import List, Optional

from mvt.android.modules.backup.base import BackupExtraction
from mvt.android.modules.backup.helpers import prompt_or_load_android_backup_password
from mvt.android.parsers.backup import (
    AndroidBackupParsingError,
    InvalidBackupPassword,
    parse_ab_header,
    parse_backup_file,
)
from mvt.common.command import Command

from .modules.backup import BACKUP_MODULES

log = logging.getLogger(__name__)


class CmdAndroidCheckBackup(Command):
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

        self.name = "check-backup"
        self.modules = BACKUP_MODULES

        self.backup_type: str = ""
        self.backup_archive: Optional[tarfile.TarFile] = None
        self.backup_files: List[str] = []

    def init(self) -> None:
        if not self.target_path:
            return

        if os.path.isfile(self.target_path):
            self.backup_type = "ab"
            with open(self.target_path, "rb") as handle:
                data = handle.read()

            header = parse_ab_header(data)
            if not header["backup"]:
                log.critical("Invalid backup format, file should be in .ab format")
                sys.exit(1)

            password = None
            if header["encryption"] != "none":
                password = prompt_or_load_android_backup_password(
                    log, self.module_options
                )
                if not password:
                    log.critical("No backup password provided.")
                    sys.exit(1)
            try:
                tardata = parse_backup_file(data, password=password)
            except InvalidBackupPassword:
                log.critical("Invalid backup password")
                sys.exit(1)
            except AndroidBackupParsingError as exc:
                log.critical("Impossible to parse this backup file: %s", exc)
                log.critical("Please use Android Backup Extractor (ABE) instead")
                sys.exit(1)

            dbytes = io.BytesIO(tardata)
            self.backup_archive = tarfile.open(fileobj=dbytes)
            for member in self.backup_archive:
                self.backup_files.append(member.name)

        elif os.path.isdir(self.target_path):
            self.backup_type = "folder"
            self.target_path = Path(self.target_path).absolute().as_posix()
            for root, subdirs, subfiles in os.walk(os.path.abspath(self.target_path)):
                for fname in subfiles:
                    self.backup_files.append(
                        os.path.relpath(os.path.join(root, fname), self.target_path)
                    )
        else:
            log.critical(
                "Invalid backup path, path should be a folder or an "
                "Android Backup (.ab) file"
            )
            sys.exit(1)

    def module_init(self, module: BackupExtraction) -> None:  # type: ignore[override]
        if self.backup_type == "folder":
            module.from_folder(self.target_path, self.backup_files)
        else:
            module.from_ab(self.target_path, self.backup_archive, self.backup_files)
