# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import json
import os
import zlib

from mvt.common.module import MVTModule
from mvt.common.utils import check_for_links


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
            if not "body" in message:
                continue

            message_links = check_for_links(message["body"])
            if self.indicators.check_domains(message_links):
                self.detected.append(message)

    def _process_sms_file(self, file_path):
        self.log.info("Processing SMS backup file at %s", file_path)

        with open(file_path, "rb") as handle:
            data = zlib.decompress(handle.read())
            json_data = json.loads(data)

        for entry in json_data:
            message_links = check_for_links(entry["body"])

            # If we find links in the messages or if they are empty we add them to the list.
            if message_links or entry["body"].strip() == "":
                self.results.append(entry)

    def run(self):
        app_folder = os.path.join(self.base_folder,
                                  "apps",
                                  "com.android.providers.telephony",
                                  "d_f")
        if not os.path.exists(app_folder):
            raise FileNotFoundError("Unable to find the SMS backup folder")

        for file_name in os.listdir(app_folder):
            if not file_name.endswith("_sms_backup"):
                continue

            file_path = os.path.join(app_folder, file_name)
            self._process_sms_file(file_path)

        self.log.info("Extracted a total of %d SMS messages containing links",
                      len(self.results))
