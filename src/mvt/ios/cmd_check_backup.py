# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
from typing import Optional

from mvt.common.command import Command
from mvt.common.indicators import Indicators

from .modules.backup import BACKUP_MODULES
from .modules.mixed import MIXED_MODULES

log = logging.getLogger(__name__)


def is_ios_backup_folder(path: str) -> bool:
    return os.path.isfile(os.path.join(path, "Manifest.db")) and os.path.isfile(
        os.path.join(path, "Info.plist")
    )


class CmdIOSCheckBackup(Command):
    def __init__(
        self,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        ioc_files: Optional[list] = None,
        iocs: Optional[Indicators] = None,
        module_name: Optional[str] = None,
        serial: Optional[str] = None,
        module_options: Optional[dict] = None,
        hashes: bool = False,
        sub_command: bool = False,
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

        self.name = "check-backup"
        self.modules = BACKUP_MODULES + MIXED_MODULES

    def resolve_backup_path(self) -> bool:
        if not self.target_path:
            return False

        if is_ios_backup_folder(self.target_path):
            return True

        if not os.path.isdir(self.target_path):
            self.log.critical(
                "%s does not appear to be an iTunes backup folder. "
                "Expected Manifest.db and Info.plist.",
                self.target_path,
            )
            return False

        candidates = []
        for entry_name in sorted(os.listdir(self.target_path)):
            entry_path = os.path.join(self.target_path, entry_name)
            if os.path.isdir(entry_path) and is_ios_backup_folder(entry_path):
                candidates.append(entry_path)

        if len(candidates) == 1:
            self.log.info("Found iTunes backup in subfolder: %s", candidates[0])
            self.target_path = candidates[0]
            return True

        if candidates:
            self.log.critical(
                "Found multiple iTunes backups in %s. Please specify one backup folder.",
                self.target_path,
            )
            return False

        self.log.critical(
            "%s does not appear to be an iTunes backup folder. "
            "Expected Manifest.db and Info.plist.",
            self.target_path,
        )
        return False

    def module_init(self, module):
        module.is_backup = True
