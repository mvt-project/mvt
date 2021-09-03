# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import plistlib

from mvt.common.utils import convert_timestamp_to_iso

from ..base import IOSExtraction

OSANALYTICS_ADDAILY_BACKUP_IDS = [
    "f65b5fafc69bbd3c60be019c6e938e146825fa83",
]
OSANALYTICS_ADDAILY_ROOT_PATHS = [
    "private/var/mobile/Library/Preferences/com.apple.osanalytics.addaily.plist",
]

class OSAnalyticsADDaily(IOSExtraction):
    """Extract network usage information by process, from com.apple.osanalytics.addaily.plist"""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record):
        record_data = f"{record['package']} WIFI IN: {record['wifi_in']}, WIFI OUT: {record['wifi_out']} - "  \
                      f"WWAN IN: {record['wwan_in']}, WWAN OUT: {record['wwan_out']}"

        records = [{
            "timestamp": record["ts"],
            "module": self.__class__.__name__,
            "event": "date",
            "data": record_data,
        }]

        return records
    
    def check_indicators(self):
        if not self.indicators:
            return

        for result in self.results:
            if self.indicators.check_process(result["package"]):
                    self.detected.append(result)

    def run(self):
        self._find_ios_database(backup_ids=OSANALYTICS_ADDAILY_BACKUP_IDS,
                                root_paths=OSANALYTICS_ADDAILY_ROOT_PATHS)
        self.log.info("Found com.apple.osanalytics.addaily plist at path: %s", self.file_path)

        with open(self.file_path, "rb") as handle:
            file_plist = plistlib.load(handle)

        for app in file_plist.get("netUsageBaseline"):
            result = {}
            result_list = file_plist.get("netUsageBaseline").get(app)
            
            if type(result_list) is list:
                result["package"] = app
                result["ts"] = convert_timestamp_to_iso(result_list[0])
                result["wifi_in"] = result_list[1]
                result["wifi_out"] = result_list[2]
                result["wwan_in"] = result_list[3]
                result["wwan_out"] = result_list[4]

                self.results.append(result)

        self.log.info("Extracted a total of %d com.apple.osanalytics.addaily entries", len(self.results))
