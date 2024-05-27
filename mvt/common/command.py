# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import json
import logging
import os
import sys
from datetime import datetime
from typing import Optional

from mvt.common.indicators import Indicators
from mvt.common.module import MVTModule, run_module, save_timeline
from mvt.common.utils import (
    convert_datetime_to_iso,
    generate_hashes_from_path,
    get_sha256_from_file_path,
)
from mvt.common.version import MVT_VERSION


class Command:
    def __init__(
        self,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        ioc_files: Optional[list] = None,
        module_name: Optional[str] = None,
        serial: Optional[str] = None,
        module_options: Optional[dict] = None,
        hashes: bool = False,
        log: logging.Logger = logging.getLogger(__name__),
    ) -> None:
        self.name = ""
        self.modules = []

        self.target_path = target_path
        self.results_path = results_path
        self.ioc_files = ioc_files if ioc_files else []
        self.module_name = module_name
        self.serial = serial
        self.log = log

        # This dictionary can contain options that will be passed down from
        # the Command to all modules. This can for example be used to pass
        # down a password to decrypt a backup or flags which are need by some modules.
        self.module_options = module_options if module_options else {}

        # This list will contain all executed modules.
        # We can use this to reference e.g. self.executed[0].results.
        self.executed = []
        self.detected_count = 0
        self.hashes = hashes
        self.hash_values = []
        self.timeline = []
        self.timeline_detected = []

        # Load IOCs
        self._create_storage()
        self._setup_logging()
        self.iocs = Indicators(log=log)
        self.iocs.load_indicators_files(self.ioc_files)

    def _create_storage(self) -> None:
        if self.results_path and not os.path.exists(self.results_path):
            try:
                os.makedirs(self.results_path)
            except Exception as exc:
                self.log.critical(
                    "Unable to create output folder %s: %s", self.results_path, exc
                )
                sys.exit(1)

    def _setup_logging(self):
        if not self.results_path:
            return

        logger = logging.getLogger("mvt")
        file_handler = logging.FileHandler(
            os.path.join(self.results_path, "command.log")
        )
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - " "%(levelname)s - %(message)s"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        # MVT can be run in a loop
        # Old file handlers stick around in subsequent loops
        # Remove any existing logging.FileHandler instances
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                logger.removeHandler(handler)

        # And finally add the new one
        logger.addHandler(file_handler)

    def _store_timeline(self) -> None:
        if not self.results_path:
            return

        if len(self.timeline) > 0:
            save_timeline(
                self.timeline, os.path.join(self.results_path, "timeline.csv")
            )

        if len(self.timeline_detected) > 0:
            save_timeline(
                self.timeline_detected,
                os.path.join(self.results_path, "timeline_detected.csv"),
            )

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

        if self.target_path and (os.environ.get("MVT_HASH_FILES") or self.hashes):
            self.generate_hashes()

        info["hashes"] = self.hash_values

        info_path = os.path.join(self.results_path, "info.json")
        with open(info_path, "w+", encoding="utf-8") as handle:
            json.dump(info, handle, indent=4)

        if self.target_path and (os.environ.get("MVT_HASH_FILES") or self.hashes):
            info_hash = get_sha256_from_file_path(info_path)
            self.log.info('Reference hash of the info.json file: "%s"', info_hash)

    def generate_hashes(self) -> None:
        """
        Compute hashes for files in the target_path
        """
        if not self.target_path:
            return

        for file in generate_hashes_from_path(self.target_path, self.log):
            self.hash_values.append(file)

    def list_modules(self) -> None:
        self.log.info("Following is the list of available %s modules:", self.name)
        for module in self.modules:
            self.log.info(" - %s", module.__name__)

    def init(self) -> None:
        raise NotImplementedError

    def module_init(self, module: MVTModule) -> None:
        raise NotImplementedError

    def finish(self) -> None:
        raise NotImplementedError

    def _show_disable_adb_warning(self) -> None:
        """Warn if ADB is enabled"""
        if type(self).__name__ in ["CmdAndroidCheckADB", "CmdAndroidCheckAndroidQF"]:
            self.log.info(
                "Please disable Developer Options and ADB (Android Debug Bridge) on the device once finished with the acquisition. "
                "ADB is a powerful tool which can allow unauthorized access to the device."
            )

    def _show_support_message(self) -> None:
        support_message = "Please seek reputable expert help if you have serious concerns about a possible spyware attack. Such support is available to human rights defenders and civil society through Amnesty International's Security Lab at https://securitylab.amnesty.org/get-help/?c=mvt"
        if self.detected_count == 0:
            self.log.info(
                f"[bold]NOTE:[/bold] Using MVT with public indicators of compromise (IOCs) [bold]WILL NOT[/bold] automatically detect advanced attacks.\n\n{support_message}",
                extra={"markup": True},
            )
        else:
            self.log.warning(
                f"[bold]NOTE: Detected indicators of compromise[/bold]. Only expert review can confirm if the detected indicators are signs of an attack.\n\n{support_message}",
                extra={"markup": True},
            )

    def run(self) -> None:
        try:
            self.init()
        except NotImplementedError:
            pass

        for module in self.modules:
            if self.module_name and module.__name__ != self.module_name:
                continue

            # FIXME: do we need the logger here
            module_logger = logging.getLogger(module.__module__)

            m = module(
                target_path=self.target_path,
                results_path=self.results_path,
                module_options=self.module_options,
                log=module_logger,
            )

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

            self.detected_count += len(m.detected)

            self.timeline.extend(m.timeline)
            self.timeline_detected.extend(m.timeline_detected)

        try:
            self.finish()
        except NotImplementedError:
            pass

        self._store_timeline()
        self._store_info()

        self._show_disable_adb_warning()
        self._show_support_message()
