# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from mvt.android.modules.backup.base import BackupExtraction
from mvt.android.parsers.backup import parse_sms_file
from mvt.common.utils import check_for_links


class SMS(BackupExtraction):
    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)
        self.results = []

    def check_indicators(self):
        if not self.indicators:
            return

        for message in self.results:
            if "body" not in message:
                continue

            if self.indicators.check_domains(message["links"]):
                self.detected.append(message)

    def run(self):
        for file in self._get_files_by_pattern("apps/com.android.providers.telephony/d_f/*_sms_backup"):
            self.log.info("Processing SMS backup file at %s", file)
            data = self._get_file_content(file)
            self.results.extend(parse_sms_file(data))
        self.log.info("Extracted a total of %d SMS messages containing links",
                      len(self.results))
