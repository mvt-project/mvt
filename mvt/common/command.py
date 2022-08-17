# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import hashlib
import json
import logging
import os
import sys
from datetime import datetime
from typing import Callable, Optional

from mvt.common.indicators import Indicators
from mvt.common.module import run_module, save_timeline
from mvt.common.utils import convert_datetime_to_iso
from mvt.common.version import MVT_VERSION


class Command:

    def __init__(
        self,
        target_path: Optional[str] = "",
        results_path: Optional[str] = "",
        ioc_files: Optional[list] = None,
        module_name: Optional[str] = "",
        serial: Optional[str] = "",
        fast_mode: Optional[bool] = False,
        log: logging.Logger = logging.getLogger(__name__),
    ) -> None:
        self.name = ""
        self.modules = []

        self.target_path = target_path
        self.results_path = results_path
        self.ioc_files = ioc_files
        self.module_name = module_name
        self.serial = serial
        self.fast_mode = fast_mode
        self.log = log

        self.iocs = Indicators(log=log)
        self.iocs.load_indicators_files(ioc_files)

        # This list will contain all executed modules.
        # We can use this to reference e.g. self.executed[0].results.
        self.executed = []

        self.timeline = []
        self.timeline_detected = []

    def _create_storage(self) -> None:
        if self.results_path and not os.path.exists(self.results_path):
            try:
                os.makedirs(self.results_path)
            except Exception as exc:
                self.log.critical("Unable to create output folder %s: %s",
                                  self.results_path, exc)
                sys.exit(1)

    def _add_log_file_handler(self, logger: logging.Logger) -> None:
        if not self.results_path:
            return

        file_handler = logging.FileHandler(os.path.join(self.results_path,
                                                        "command.log"))
        formatter = logging.Formatter("%(asctime)s - %(name)s - "
                                      "%(levelname)s - %(message)s")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    def _store_timeline(self) -> None:
        if not self.results_path:
            return

        if len(self.timeline) > 0:
            save_timeline(self.timeline,
                          os.path.join(self.results_path, "timeline.csv"))

        if len(self.timeline_detected) > 0:
            save_timeline(self.timeline_detected,
                          os.path.join(self.results_path,
                                       "timeline_detected.csv"))

    def _store_info(self) -> None:
        if not self.results_path:
            return

        target_path = None
        if self.target_path:
            target_path = os.path.abspath(self.target_path)

        info = {
            "target_path": target_path,
            "mvt_version": MVT_VERSION,
            "date": convert_datetime_to_iso(datetime.now()),
            "ioc_files": [],
            "hashes": [],
        }

        for coll in self.iocs.ioc_collections:
            ioc_file_path = coll.get("stix2_file_path", "")
            if ioc_file_path and ioc_file_path not in info["ioc_files"]:
                info["ioc_files"].append(ioc_file_path)

        # TODO: Revisit if setting this from environment variable is good
        #       enough.
        if self.target_path and os.environ.get("MVT_HASH_FILES"):
            if os.path.isfile(self.target_path):
                sha256 = hashlib.sha256()
                with open(self.target_path, "rb") as handle:
                    sha256.update(handle.read())

                info["hashes"].append({
                    "file_path": self.target_path,
                    "sha256": sha256.hexdigest(),
                })
            elif os.path.isdir(self.target_path):
                for (root, _, files) in os.walk(self.target_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        sha256 = hashlib.sha256()

                        try:
                            with open(file_path, "rb") as handle:
                                sha256.update(handle.read())
                        except FileNotFoundError:
                            self.log.error("Failed to hash the file %s: might be a symlink",
                                           file_path)
                            continue
                        except PermissionError:
                            self.log.error("Failed to hash the file %s: permission denied",
                                           file_path)
                            continue

                        info["hashes"].append({
                            "file_path": file_path,
                            "sha256": sha256.hexdigest(),
                        })

        info_path = os.path.join(self.results_path, "info.json")
        with open(info_path, "w+", encoding="utf-8") as handle:
            json.dump(info, handle, indent=4)

    def list_modules(self) -> None:
        self.log.info("Following is the list of available %s modules:",
                      self.name)
        for module in self.modules:
            self.log.info(" - %s", module.__name__)

    def init(self) -> None:
        raise NotImplementedError

    def module_init(self, module: Callable) -> None:
        raise NotImplementedError

    def finish(self) -> None:
        raise NotImplementedError

    def run(self) -> None:
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

            self.executed.append(m)

            self.timeline.extend(m.timeline)
            self.timeline_detected.extend(m.timeline_detected)

        self._store_timeline()
        self._store_info()

        try:
            self.finish()
        except NotImplementedError:
            pass
