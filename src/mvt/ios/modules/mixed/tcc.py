# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import sqlite3
from typing import Optional, Union

from mvt.common.utils import convert_unix_to_iso

from ..base import IOSExtraction

TCC_BACKUP_IDS = [
    "64d0019cb3d46bfc8cce545a8ba54b93e7ea9347",
]
TCC_ROOT_PATHS = [
    "private/var/mobile/Library/TCC/TCC.db",
]

AUTH_VALUE_OLD = {0: "denied", 1: "allowed"}
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

    def serialize(self, record: dict) -> Union[dict, list]:
        if "last_modified" in record:
            if "allowed_value" in record:
                msg = (
                    f"Access to {record['service']} by {record['client']} "
                    f"{record['allowed_value']}"
                )
            else:
                msg = (
                    f"Access to {record['service']} by {record['client']} "
                    f"{record['auth_value']}"
                )

            return {
                "timestamp": record["last_modified"],
                "module": self.__class__.__name__,
                "event": "AccessRequest",
                "data": msg,
            }

        return {}

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_process(result["client"])
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)

    def process_db(self, file_path):
        conn = self._open_sqlite_db(file_path)
        cur = conn.cursor()
        db_version = "v3"
        try:
            cur.execute(
                """SELECT
                service, client, client_type, auth_value,
                auth_reason, last_modified
            FROM access;"""
            )
        except sqlite3.OperationalError:
            # v2 version
            try:
                cur.execute(
                    """SELECT
                    service, client, client_type, allowed,
                    prompt_count, last_modified
                    FROM access;"""
                )
                db_version = "v2"
            except sqlite3.OperationalError:
                try:
                    cur.execute(
                        """SELECT
                        service, client, client_type, allowed,
                        prompt_count
                        FROM access;"""
                    )
                    db_version = "v1"
                except sqlite3.OperationalError as e:
                    self.log.error(f"Error parsing TCC database: {e}")

        for row in cur:
            service = row[0]
            client = row[1]
            client_type = row[2]
            client_type_desc = "bundle_id" if client_type == 0 else "absolute_path"
            if db_version == "v3":
                auth_value = row[3]
                auth_value_desc = AUTH_VALUES.get(auth_value, "")
                auth_reason = row[4]
                auth_reason_desc = AUTH_REASONS.get(auth_reason, "unknown")
                last_modified = convert_unix_to_iso(row[5])

                if service in ["kTCCServiceMicrophone", "kTCCServiceCamera"]:
                    device = (
                        "microphone" if service == "kTCCServiceMicrophone" else "camera"
                    )
                    self.log.info(
                        'Found client "%s" with access %s to %s on %s by %s',
                        client,
                        auth_value_desc,
                        device,
                        last_modified,
                        auth_reason_desc,
                    )

                self.results.append(
                    {
                        "service": service,
                        "client": client,
                        "client_type": client_type_desc,
                        "auth_value": auth_value_desc,
                        "auth_reason_desc": auth_reason_desc,
                        "last_modified": last_modified,
                    }
                )
            else:
                allowed_value = row[3]
                allowed_desc = AUTH_VALUE_OLD.get(allowed_value, "")
                prompt_count = row[4]

                if db_version == "v2":
                    last_modified = convert_unix_to_iso(row[5])
                    if service in ["kTCCServiceMicrophone", "kTCCServiceCamera"]:
                        device = "camera"
                        if service == "kTCCServiceMicrophone":
                            device = "microphone"

                        self.log.info(
                            'Found client "%s" with access %s to %s at %s',
                            client,
                            allowed_desc,
                            device,
                            last_modified,
                        )

                    self.results.append(
                        {
                            "service": service,
                            "client": client,
                            "client_type": client_type_desc,
                            "allowed_value": allowed_desc,
                            "prompt_count": prompt_count,
                            "last_modified": last_modified,
                        }
                    )
                else:
                    if service in ["kTCCServiceMicrophone", "kTCCServiceCamera"]:
                        device = "camera"
                        if service == "kTCCServiceMicrophone":
                            device = "microphone"

                        self.log.info(
                            'Found client "%s" with access %s to %s',
                            client,
                            allowed_desc,
                            device,
                        )

                    self.results.append(
                        {
                            "service": service,
                            "client": client,
                            "client_type": client_type_desc,
                            "allowed_value": allowed_desc,
                            "prompt_count": prompt_count,
                        }
                    )

        cur.close()
        conn.close()

    def run(self) -> None:
        self._find_ios_database(backup_ids=TCC_BACKUP_IDS, root_paths=TCC_ROOT_PATHS)
        self.log.info("Found TCC database at path: %s", self.file_path)

        self.process_db(self.file_path)

        self.log.info("Extracted a total of %d TCC items", len(self.results))
