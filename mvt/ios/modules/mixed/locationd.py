# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import base64
import logging
import plistlib
from typing import Optional, Union

from mvt.common.utils import convert_mactime_to_iso

from ..base import IOSExtraction

LOCATIOND_BACKUP_IDS = [
    "a690d7769cce8904ca2b67320b107c8fe5f79412",
]
LOCATIOND_ROOT_PATHS = [
    "private/var/mobile/Library/Caches/locationd/clients.plist",
    "private/var/root/Library/Caches/locationd/clients.plist",
]


class LocationdClients(IOSExtraction):
    """Extract information from apps who used geolocation."""

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

        self.timestamps = [
            "ConsumptionPeriodBegin",
            "ReceivingLocationInformationTimeStopped",
            "VisitTimeStopped",
            "LocationTimeStopped",
            "BackgroundLocationTimeStopped",
            "SignificantTimeStopped",
            "NonPersistentSignificantTimeStopped",
            "FenceTimeStopped",
            "BeaconRegionTimeStopped",
        ]

    def serialize(self, record: dict) -> Union[dict, list]:
        records = []
        for timestamp in self.timestamps:
            if timestamp in record.keys():
                records.append(
                    {
                        "timestamp": record[timestamp],
                        "module": self.__class__.__name__,
                        "event": timestamp,
                        "data": f"{timestamp} from {record['package']}",
                    }
                )

        return records

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            parts = result["package"].split("/")
            proc_name = parts[len(parts) - 1]

            ioc = self.indicators.check_process(proc_name)
            if ioc:
                self.log.warning(
                    "Found a suspicious process name in LocationD entry %s",
                    result["package"],
                )
                result["matched_indicator"] = ioc
                self.detected.append(result)
                continue

            if "BundleId" in result:
                ioc = self.indicators.check_process(result["BundleId"])
                if ioc:
                    self.log.warning(
                        "Found a suspicious process name in LocationD entry %s",
                        result["package"],
                    )
                    result["matched_indicator"] = ioc

            if "BundlePath" in result:
                ioc = self.indicators.check_file_path(result["BundlePath"])
                if ioc:
                    self.log.warning(
                        "Found a suspicious file path in Location D: %s",
                        result["BundlePath"],
                    )
                    result["matched_indicator"] = ioc
                    self.detected.append(result)
                    continue

            if "Executable" in result:
                ioc = self.indicators.check_file_path(result["Executable"])
                if ioc:
                    self.log.warning(
                        "Found a suspicious file path in Location D: %s",
                        result["Executable"],
                    )
                    result["matched_indicator"] = ioc
                    self.detected.append(result)
                    continue

            if "Registered" in result:
                # Sometimes registered is a bool
                if isinstance(result["Registered"], bool):
                    continue
                ioc = self.indicators.check_file_path(result["Registered"])
                if ioc:
                    self.log.warning(
                        "Found a suspicious file path in Location D: %s",
                        result["Registered"],
                    )
                    result["matched_indicator"] = ioc
                    self.detected.append(result)
                    continue

    def _extract_locationd_entries(self, file_path):
        with open(file_path, "rb") as handle:
            file_plist = plistlib.load(handle)

        for key, _ in file_plist.items():
            # Some migration information are int and not dicts
            if not isinstance(file_plist[key], dict):
                continue
            # FIXME: unclear key format in iOS 17
            result = file_plist[key]
            result["package"] = key.rstrip(":")
            for timestamp in self.timestamps:
                if timestamp in result.keys():
                    result[timestamp] = convert_mactime_to_iso(result[timestamp])

            if "ClientStorageToken" in result:
                result["ClientStorageToken"] = base64.b64encode(
                    result["ClientStorageToken"]
                )

            self.results.append(result)

    def run(self) -> None:
        if self.is_backup:
            self._find_ios_database(backup_ids=LOCATIOND_BACKUP_IDS)
            self.log.info("Found Locationd Clients plist at path: %s", self.file_path)
            self._extract_locationd_entries(self.file_path)
        elif self.is_fs_dump:
            for locationd_path in self._get_fs_files_from_patterns(
                LOCATIOND_ROOT_PATHS
            ):
                self.file_path = locationd_path
                self.log.info(
                    "Found Locationd Clients plist at path: %s", self.file_path
                )
                self._extract_locationd_entries(self.file_path)

        self.log.info(
            "Extracted a total of %d Locationd Clients entries", len(self.results)
        )
