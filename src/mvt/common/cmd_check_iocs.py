# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
from typing import Optional

from mvt.common.command import Command
from mvt.common.utils import exec_or_profile

log = logging.getLogger(__name__)


class CmdCheckIOCS(Command):
    def __init__(
        self,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        ioc_files: Optional[list] = None,
        module_name: Optional[str] = None,
        serial: Optional[str] = None,
        module_options: Optional[dict] = None,
    ) -> None:
        super().__init__(
            target_path=target_path,
            results_path=results_path,
            ioc_files=ioc_files,
            module_name=module_name,
            serial=serial,
            module_options=module_options,
            log=log,
        )

        self.name = "check-iocs"

    def run(self) -> None:
        assert self.target_path is not None
        all_modules = []
        for entry in self.modules:
            if entry not in all_modules:
                all_modules.append(entry)

        log.info("Checking stored results against provided indicators...")

        total_detections = 0
        for file_name in os.listdir(self.target_path):
            name_only, _ = os.path.splitext(file_name)
            file_path = os.path.join(self.target_path, file_name)

            for iocs_module in all_modules:
                if self.module_name and iocs_module.__name__ != self.module_name:
                    continue

                if iocs_module.get_slug() != name_only:
                    continue

                log.info(
                    'Loading results from "%s" with module %s',
                    file_name,
                    iocs_module.__name__,
                )

                m = iocs_module.from_json(
                    file_path, log=logging.getLogger(iocs_module.__module__)
                )
                if self.iocs.total_ioc_count > 0:
                    m.indicators = self.iocs
                    m.indicators.log = m.log

                try:
                    exec_or_profile("m.check_indicators()", globals(), locals())
                except NotImplementedError:
                    continue
                else:
                    total_detections += len(m.detected)

        if total_detections > 0:
            log.warning(
                "The check of the results produced %d detections!", total_detections
            )
