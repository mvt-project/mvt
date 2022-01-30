# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import plistlib

from mvt.common.utils import convert_mactime_to_unix, convert_timestamp_to_iso

from ..base import IOSExtraction

LOCATIOND_BACKUP_IDS = [
    "a690d7769cce8904ca2b67320b107c8fe5f79412",
]
LOCATIOND_ROOT_PATHS = [
    "private/var/mobile/Library/Caches/locationd/clients.plist",
    "private/var/root/Library/Caches/locationd/clients.plist"
]


class LocationdClients(IOSExtraction):
    """Extract information from apps who used geolocation."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

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

    def serialize(self, record):
        records = []
        for timestamp in self.timestamps:
            if timestamp in record.keys():
                records.append({
                    "timestamp": record[timestamp],
                    "module": self.__class__.__name__,
                    "event": timestamp,
                    "data": f"{timestamp} from {record['package']}"
                })

        return records

    def check_indicators(self):
        if not self.indicators:
            return

        for result in self.results:
            parts = result["package"].split("/")
            proc_name = parts[len(parts)-1]

            ioc = self.indicators.check_process(proc_name)
            if ioc:
                self.log.warning("Found a suspicious process name in LocationD entry %s",
                                 result["package"])
                result["matched_indicator"] = ioc
                self.detected.append(result)
                continue

            if "BundlePath" in result:
                ioc = self.indicators.check_file_path(result["BundlePath"])
                if ioc:
                    self.log.warning("Found a suspicious file path in Location D: %s",
                                     result["BundlePath"])
                    result["matched_indicator"] = ioc
                    self.detected.append(result)
                    continue

            if "Executable" in result:
                ioc = self.indicators.check_file_path(result["Executable"])
                if ioc:
                    self.log.warning("Found a suspicious file path in Location D: %s",
                                     result["Executable"])
                    result["matched_indicator"] = ioc
                    self.detected.append(result)
                    continue

            if "Registered" in result:
                ioc = self.indicators.check_file_path(result["Registered"])
                if ioc:
                    self.log.warning("Found a suspicious file path in Location D: %s",
                                     result["Registered"])
                    result["matched_indicator"] = ioc
                    self.detected.append(result)
                    continue

    def _extract_locationd_entries(self, file_path):
        with open(file_path, "rb") as handle:
            file_plist = plistlib.load(handle)

        for key, values in file_plist.items():
            result = file_plist[key]
            result["package"] = key
            for ts in self.timestamps:
                if ts in result.keys():
                    result[ts] = convert_timestamp_to_iso(convert_mactime_to_unix(result[ts]))

            self.results.append(result)

    def run(self):

        if self.is_backup:
            self._find_ios_database(backup_ids=LOCATIOND_BACKUP_IDS)
            self.log.info("Found Locationd Clients plist at path: %s", self.file_path)
            self._extract_locationd_entries(self.file_path)
        elif self.is_fs_dump:
            for locationd_path in self._get_fs_files_from_patterns(LOCATIOND_ROOT_PATHS):
                self.file_path = locationd_path
                self.log.info("Found Locationd Clients plist at path: %s", self.file_path)
                self._extract_locationd_entries(self.file_path)

        self.log.info("Extracted a total of %d Locationd Clients entries", len(self.results))
