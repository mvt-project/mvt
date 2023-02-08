# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional

from mvt.common.command import Command

from .modules.androidqf import ANDROIDQF_MODULES

log = logging.getLogger(__name__)


class CmdAndroidCheckAndroidQF(Command):

    def __init__(
        self,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        ioc_files: Optional[list] = None,
        module_name: Optional[str] = None,
        serial: Optional[str] = None,
        fast_mode: Optional[bool] = False,
    ) -> None:
        super().__init__(target_path=target_path, results_path=results_path,
                         ioc_files=ioc_files, module_name=module_name,
                         serial=serial, fast_mode=fast_mode, log=log)

        self.name = "check-androidqf"
        self.modules = ANDROIDQF_MODULES
