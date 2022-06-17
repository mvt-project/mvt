# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
import plistlib

from mvt.common.module import DatabaseNotFoundError
from mvt.ios.versions import latest_ios_version

from ..base import IOSExtraction


class BackupInfo(IOSExtraction):
    """This module extracts information about the device and the backup."""

    def __init__(self, file_path: str = None, target_path: str = None,
                 results_path: str = None, fast_mode: bool = False,
                 log: logging.Logger = None, results: list = []) -> None:
        super().__init__(file_path=file_path, target_path=target_path,
                         results_path=results_path, fast_mode=fast_mode,
                         log=log, results=results)

        self.results = {}

    def run(self) -> None:
        info_path = os.path.join(self.target_path, "Info.plist")
        if not os.path.exists(info_path):
            raise DatabaseNotFoundError("No Info.plist at backup path, unable to extract device information")

        with open(info_path, "rb") as handle:
            info = plistlib.load(handle)

        fields = ["Build Version", "Device Name", "Display Name",
                  "GUID", "ICCID", "IMEI", "MEID", "Installed Applications",
                  "Last Backup Date", "Phone Number", "Product Name",
                  "Product Type", "Product Version", "Serial Number",
                  "Target Identifier", "Target Type", "Unique Identifier",
                  "iTunes Version"]

        for field in fields:
            value = info.get(field, None)
            self.log.info("%s: %s", field, value)
            self.results[field] = value

        if "Product Version" in info:
            latest = latest_ios_version()
            if info["Product Version"] != latest["version"]:
                self.log.warning("This phone is running an outdated iOS version: %s (latest is %s)",
                                 info["Product Version"], latest['version'])
