# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import sqlite3

from mvt.common.utils import convert_mactime_to_unix, convert_timestamp_to_iso

from ..base import IOSExtraction

CALLS_BACKUP_IDS = [
    "5a4935c78a5255723f707230a451d79c540d2741",
]
CALLS_ROOT_PATHS = [
    "private/var/mobile/Library/CallHistoryDB/CallHistory.storedata"
]


class Calls(IOSExtraction):
    """This module extracts phone calls details"""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record):
        return {
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": "call",
            "data": f"From {record['number']} using {record['provider']} during {record['duration']} seconds"
        }

    def run(self):
        self._find_ios_database(backup_ids=CALLS_BACKUP_IDS,
                                root_paths=CALLS_ROOT_PATHS)
        self.log.info("Found Calls database at path: %s", self.file_path)

        conn = sqlite3.connect(self.file_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT
                ZDATE, ZDURATION, ZLOCATION, ZADDRESS, ZSERVICE_PROVIDER
            FROM ZCALLRECORD;
        """)
        # names = [description[0] for description in cur.description]

        for row in cur:
            self.results.append({
                "isodate": convert_timestamp_to_iso(convert_mactime_to_unix(row[0])),
                "duration": row[1],
                "location": row[2],
                "number": row[3].decode("utf-8") if row[3] and row[3] is bytes else row[3],
                "provider": row[4]
            })

        cur.close()
        conn.close()

        self.log.info("Extracted a total of %d calls", len(self.results))
