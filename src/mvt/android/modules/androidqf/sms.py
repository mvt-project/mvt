# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1

import logging
from typing import Optional

from mvt.android.modules.backup.helpers import prompt_or_load_android_backup_password
from mvt.android.parsers.backup import (
    AndroidBackupParsingError,
    InvalidBackupPassword,
    parse_ab_header,
    parse_backup_file,
    parse_tar_for_sms,
)

from .base import AndroidQFModule


class SMS(AndroidQFModule):
    """This module analyse SMS file in backup"""

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        module_options: Optional[dict] = None,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[list] = None,
    ) -> None:
        super().__init__(
            file_path=file_path,
            target_path=target_path,
            results_path=results_path,
            module_options=module_options,
            log=log,
            results=results,
        )

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for message in self.results:
            if "body" not in message:
                continue

            if self.indicators.check_domains(message.get("links", [])):
                self.detected.append(message)

    def parse_backup(self, data):
        header = parse_ab_header(data)
        if not header["backup"]:
            self.log.critical("Invalid backup format, backup.ab was not analysed")
            return

        password = None
        if header["encryption"] != "none":
            password = prompt_or_load_android_backup_password(
                self.log, self.module_options
            )
            if not password:
                self.log.critical("No backup password provided.")
                return

        try:
            tardata = parse_backup_file(data, password=password)
        except InvalidBackupPassword:
            self.log.critical("Invalid backup password")
            return
        except AndroidBackupParsingError:
            self.log.critical(
                "Impossible to parse this backup file, please use"
                " Android Backup Extractor instead"
            )
            return

        if not tardata:
            return

        try:
            self.results = parse_tar_for_sms(tardata)
        except AndroidBackupParsingError:
            self.log.info(
                "Impossible to read SMS from the Android Backup, "
                "please extract the SMS and try extracting it with "
                "Android Backup Extractor"
            )
            return

    def run(self) -> None:
        files = self._get_files_by_pattern("*/backup.ab")
        if not files:
            self.log.info("No backup data found")
            return

        self.parse_backup(self._get_file_content(files[0]))
        self.log.info("Identified %d SMS in backup data", len(self.results))
