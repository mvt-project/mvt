# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import os
import getpass

from mvt.common.module import MVTModule
from mvt.common.utils import check_for_links
from mvt.android.parsers.backup import parse_sms_file, parse_sms_backup, parse_ab_header, InvalidBackupPassword, AndroidBackupParsingError


class SMS(MVTModule):
    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def check_indicators(self):
        if not self.indicators:
            return

        for message in self.results:
            if "body" not in message:
                continue

            message_links = check_for_links(message["body"])
            if self.indicators.check_domains(message_links):
                self.detected.append(message)

    def _process_sms_file(self, file_path):
        self.log.info("Processing SMS backup file at %s", file_path)

        with open(file_path, "rb") as handle:
            data = handle.read()

        self.results = parse_sms_file(data)

    def run(self):
        # FIXME: this should be done in the Module code if there are other modules on backups
        if os.path.isfile(self.base_folder):
            # ab file
            with open(self.base_folder, "rb") as handle:
                data = handle.read()
            header = parse_ab_header(data)
            if not header["backup"]:
                self.log.info("Not a valid Android Backup file, quitting...")
                return

            pwd = None
            if header["encryption"] != "none":
                pwd = getpass.getpass(prompt="Backup Password: ", stream=None)

            try:
                messages = parse_sms_backup(data, password=pwd)
            except InvalidBackupPassword:
                self.log.info("Invalid password, impossible de decrypt the backup, quitting...")
                return
            except AndroidBackupParsingError:
                self.log.info("Impossible to extract data from this Android Backup, please regenerate the backup using the -nocompress option or extract it using Android Backup Extractor instead.")
                self.log.info("Quitting...")
                return

            self.results = messages
        else:
            app_folder = os.path.join(self.base_folder,
                                      "apps",
                                      "com.android.providers.telephony",
                                      "d_f")
            if not os.path.exists(app_folder):
                self.log.info("Unable to find the SMS backup folder")
                return

            for file_name in os.listdir(app_folder):
                if not file_name.endswith("_sms_backup"):
                    continue

                file_path = os.path.join(app_folder, file_name)
                self._process_sms_file(file_path)

        self.log.info("Extracted a total of %d SMS messages containing links",
                      len(self.results))
