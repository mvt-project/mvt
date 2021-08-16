# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
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
]

class LocationdClients(IOSExtraction):
    """Extract information from apps who used geolocation"""

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
        for ts in self.timestamps:
            if ts in record.keys():
                records.append({
                    "timestamp": record[ts],
                    "module": self.__class__.__name__,
                    "event": ts,
                    "data": f"{ts} from {record['package']}"
                })

        return records

    def run(self):
        self._find_ios_database(backup_ids=LOCATIOND_BACKUP_IDS,
                                root_paths=LOCATIOND_ROOT_PATHS)
        self.log.info("Found Locationd Clients plist at path: %s", self.file_path)

        with open(self.file_path, "rb") as handle:
            file_plist = plistlib.load(handle)

        for app in file_plist:
            if file_plist[app] is dict:
                result = file_plist[app]
                result["package"] = app
                for ts in self.timestamps:
                    if ts in result.keys():
                        result[ts] = convert_timestamp_to_iso(convert_mactime_to_unix(result[ts]))

                self.results.append(result)

        self.log.info("Extracted a total of %d Locationd Clients entries", len(self.results))
