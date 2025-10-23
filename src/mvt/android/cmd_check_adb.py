# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional

from mvt.common.command import Command

from .modules.adb import ADB_MODULES

log = logging.getLogger(__name__)


class CmdAndroidCheckADB(Command):
    def __init__(
        self,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        ioc_files: Optional[list] = None,
        module_name: Optional[str] = None,
        serial: Optional[str] = None,
        module_options: Optional[dict] = None,
        disable_version_check: bool = False,
        disable_indicator_check: bool = False,
    ) -> None:
        super().__init__(
            target_path=target_path,
            results_path=results_path,
            ioc_files=ioc_files,
            module_name=module_name,
            serial=serial,
            module_options=module_options,
            log=log,
            disable_version_check=disable_version_check,
            disable_indicator_check=disable_indicator_check,
        )

        self.name = "check-adb"
        self.modules = ADB_MODULES
