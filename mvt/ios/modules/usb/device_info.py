# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import base64
import logging

from mvt.ios.versions import latest_ios_version

from .base import IOSUSBExtraction


class DeviceInfo(IOSUSBExtraction):
    """This class extracts all processes running on the phone."""
    def __init__(self, file_path: str = None, target_path: str = None,
                 results_path: str = None, fast_mode: bool = False,
                 log: logging.Logger = None, results: list = []) -> None:
        super().__init__(file_path=file_path, target_path=target_path,
                         results_path=results_path, fast_mode=fast_mode,
                         log=log, results=results)

    def run(self) -> None:
        self.results = self.lockdown.all_values

        # Base64 encoding of bytes
        for entry in self.results:
            if isinstance(self.results[entry], bytes):
                self.results[entry] = base64.b64encode(self.results[entry])
            elif isinstance(self.results[entry], dict):
                for second_entry in self.results[entry]:
                    if isinstance(self.results[entry][second_entry], bytes):
                        self.results[entry][second_entry] = base64.b64encode(self.results[entry][second_entry])

        if "ProductVersion" in self.results:
            latest = latest_ios_version()
            if self.results["ProductVersion"] != latest["version"]:
                self.log.warning("This phone is running an outdated iOS version: %s (latest is %s)",
                                 self.results["ProductVersion"], latest['version'])
