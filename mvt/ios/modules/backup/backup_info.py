# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
import plistlib
from typing import Optional

from mvt.common.module import DatabaseNotFoundError
from mvt.ios.versions import get_device_desc_from_id, is_ios_version_outdated

from ..base import IOSExtraction


class BackupInfo(IOSExtraction):
    """This module extracts information about the device and the backup."""

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

        self.results = {}

    def run(self) -> None:
        info_path = os.path.join(self.target_path, "Info.plist")
        if not os.path.exists(info_path):
            raise DatabaseNotFoundError(
                "No Info.plist at backup path, unable to extract device " "information"
            )

        with open(info_path, "rb") as handle:
            info = plistlib.load(handle)

        fields = [
            "Build Version",
            "Device Name",
            "Display Name",
            "GUID",
            "ICCID",
            "IMEI",
            "MEID",
            "Installed Applications",
            "Last Backup Date",
            "Phone Number",
            "Product Name",
            "Product Type",
            "Product Version",
            "Serial Number",
            "Target Identifier",
            "Target Type",
            "Unique Identifier",
            "iTunes Version",
        ]

        for field in fields:
            value = info.get(field, None)

            if field == "Product Type" and value:
                product_name = get_device_desc_from_id(value)
                if product_name:
                    self.log.info("%s: %s (%s)", field, value, product_name)
                else:
                    self.log.info("%s: %s", field, value)
            else:
                self.log.info("%s: %s", field, value)

            self.results[field] = value

        if "Product Version" in info:
            is_ios_version_outdated(info["Product Version"], log=self.log)
