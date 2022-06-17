# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
import sys

from mvt.common.indicators import Indicators
from mvt.common.module import run_module, save_timeline


class Command(object):

    def __init__(self, target_path=None, results_path=None, ioc_files=[],
                 module_name=None, serial=None, fast_mode=False,
                 log=logging.getLogger(__name__)):
        self.name = ""

        self.target_path = target_path
        self.results_path = results_path
        self.ioc_files = ioc_files
        self.module_name = module_name
        self.serial = serial
        self.fast_mode = fast_mode
        self.log = log

        self.iocs = Indicators(log=log)
        self.iocs.load_indicators_files(ioc_files)

        self.timeline = []
        self.timeline_detected = []

    def list_modules(self):
        self.log.info("Following is the list of available %s modules:", self.name)
        for module in self.modules:
            self.log.info(" - %s", module.__name__)

    def _create_storage(self):
        if self.results_path and not os.path.exists(self.results_path):
            try:
                os.makedirs(self.results_path)
            except Exception as e:
                self.log.critical("Unable to create output folder %s: %s",
                                  self.results_path, e)
                sys.exit(1)

    def _store_timeline(self):
        if self.results_path:
            return

        if len(self.timeline) > 0:
            save_timeline(self.timeline,
                          os.path.join(self.results_path, "timeline.csv"))

        if len(self.timeline_detected) > 0:
            save_timeline(self.timeline_detected,
                          os.path.join(self.results_path, "timeline_detected.csv"))

    def _add_log_file_handler(self, logger):
        if not self.results_path:
            return

        fh = logging.FileHandler(os.path.join(self.results_path, "command.log"))
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    def init(self):
        raise NotImplementedError

    def module_init(self, module):
        raise NotImplementedError

    def run(self):
        self._create_storage()
        self._add_log_file_handler(self.log)

        try:
            self.init()
        except NotImplementedError:
            pass

        for module in self.modules:
            if self.module_name and module.__name__ != self.module_name:
                continue

            module_logger = logging.getLogger(module.__module__)
            self._add_log_file_handler(module_logger)

            m = module(target_path=self.target_path,
                       results_path=self.results_path,
                       fast_mode=self.fast_mode,
                       log=module_logger)

            if self.iocs.total_ioc_count:
                m.indicators = self.iocs
                m.indicators.log = m.log

            if self.serial:
                m.serial = self.serial

            try:
                self.module_init(m)
            except NotImplementedError:
                pass

            run_module(m)

            self.timeline.extend(m.timeline)
            self.timeline_detected.extend(m.timeline_detected)

        self._store_timeline()

