# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional

from mvt.common.command import Command

from .modules.fs import FS_MODULES
from .modules.mixed import MIXED_MODULES

log = logging.getLogger(__name__)


class CmdIOSCheckFS(Command):
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

        self.name = "check-fs"
        self.modules = FS_MODULES + MIXED_MODULES

    def module_init(self, module):
        module.is_fs_dump = True
