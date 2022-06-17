# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os

from mvt.common.command import Command

log = logging.getLogger(__name__)


class CmdCheckIOCS(Command):

    name = "check-iocs"
    modules = []

    def __init__(self, target_path: str = None, results_path: str = None,
                 ioc_files: list = [], module_name: str = None, serial: str = None,
                 fast_mode: bool = False):
        super().__init__(target_path=target_path, results_path=results_path,
                         ioc_files=ioc_files, module_name=module_name,
                         serial=serial, fast_mode=fast_mode, log=log)

    def run(self) -> None:
        all_modules = []
        for entry in self.modules:
            if entry not in all_modules:
                all_modules.append(entry)

        log.info("Checking stored results against provided indicators...")

        total_detections = 0
        for file_name in os.listdir(self.target_path):
            name_only, ext = os.path.splitext(file_name)
            file_path = os.path.join(self.target_path, file_name)

            for iocs_module in all_modules:
                if self.module_name and iocs_module.__name__ != self.module_name:
                    continue

                if iocs_module().get_slug() != name_only:
                    continue

                log.info("Loading results from \"%s\" with module %s", file_name,
                         iocs_module.__name__)

                m = iocs_module.from_json(file_path,
                                          log=logging.getLogger(iocs_module.__module__))
                if self.iocs.total_ioc_count > 0:
                    m.indicators = self.iocs
                    m.indicators.log = m.log

                try:
                    m.check_indicators()
                except NotImplementedError:
                    continue
                else:
                    total_detections += len(m.detected)

        if total_detections > 0:
            log.warning("The check of the results produced %d detections!",
                        total_detections)
