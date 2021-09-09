# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import sqlite3
from datetime import datetime

from mvt.common.utils import convert_timestamp_to_iso

from ..base import IOSExtraction

TCC_BACKUP_IDS = [
    "64d0019cb3d46bfc8cce545a8ba54b93e7ea9347",
]
TCC_ROOT_PATHS = [
    "private/var/mobile/Library/TCC/TCC.db",
]

AUTH_VALUES = {
    0: "denied",
    1: "unknown",
    2: "allowed",
    3: "limited",
}
AUTH_REASONS = {
    1: "error",
    2: "user_consent",
    3: "user_set",
    4: "system_set",
    5: "service_policy",
    6: "mdm_policy",
    7: "override_policy",
    8: "missing_usage_string",
    9: "prompt_timeout",
    10: "preflight_unknown",
    11: "entitled",
    12: "app_type_policy",
}

class TCC(IOSExtraction):
    """This module extracts records from the TCC.db SQLite database."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def process_db(self, file_path):
        conn = sqlite3.connect(file_path)
        cur = conn.cursor()
        cur.execute("""SELECT 
            service, client, client_type, auth_value, auth_reason, last_modified
        FROM access;""")

        for row in cur:
            service = row[0]
            client = row[1]
            client_type = row[2]
            client_type_desc = "bundle_id" if client_type == 0 else "absolute_path"
            auth_value = row[3]
            auth_value_desc = AUTH_VALUES.get(auth_value, "")
            auth_reason = row[4]
            auth_reason_desc = AUTH_REASONS.get(auth_reason, "unknown")
            last_modified = convert_timestamp_to_iso(datetime.utcfromtimestamp((row[5])))

            if service in ["kTCCServiceMicrophone", "kTCCServiceCamera"]:
                device = "microphone" if service == "kTCCServiceMicrophone" else "camera"
                self.log.info("Found client \"%s\" with access %s to %s on %s by %s",
                              client, auth_value_desc, device, last_modified, auth_reason_desc)

            self.results.append({
                "service": service,
                "client": client,
                "client_type": client_type_desc,
                "auth_value": auth_value_desc,
                "auth_reason_desc": auth_reason_desc,
                "last_modified": last_modified,
            })

        cur.close()
        conn.close()

    def run(self):
        self._find_ios_database(backup_ids=TCC_BACKUP_IDS, root_paths=TCC_ROOT_PATHS)
        self.log.info("Found TCC database at path: %s", self.file_path)
        self.process_db(self.file_path)

        self.log.info("Extracted a total of %d TCC items", len(self.results))
