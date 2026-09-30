# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import sqlite3
from typing import Optional

from mvt.common.module_types import (
    ModuleAtomicResult,
    ModuleResults,
    ModuleSerializedResult,
)
from mvt.common.utils import convert_unix_to_iso, sanitize_json_data

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
        results: Optional[ModuleResults] = None,
    ) -> None:
        super().__init__(
            file_path=file_path,
            target_path=target_path,
            results_path=results_path,
            module_options=module_options,
            log=log,
            results=results,
        )

    def serialize(self, record: ModuleAtomicResult) -> ModuleSerializedResult:
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
            ioc_match = self.indicators.check_process(result["client"])
            if ioc_match:
                self.alertstore.critical(
                    ioc_match.message, "", result, matched_indicator=ioc_match.ioc
                )

    def process_db(self, file_path):
        conn = self._open_sqlite_db(file_path)
        cur = conn.cursor()
        try:
            try:
                cur.execute("SELECT * FROM access;")
            except sqlite3.OperationalError as exc:
                self.log.error("Error parsing TCC database: %s", exc)
                return

            names = [description[0] for description in cur.description]
            for row in cur:
                record = sanitize_json_data(dict(zip(names, row)))
                client_type = record.get("client_type")
                record["client_type_value"] = client_type
                record["client_type"] = (
                    "bundle_id" if client_type == 0 else "absolute_path"
                )

                if "auth_value" in record:
                    auth_value = record["auth_value"]
                    record["auth_value_value"] = auth_value
                    record["auth_value"] = AUTH_VALUES.get(auth_value, "unknown")
                    auth_reason = record.get("auth_reason")
                    record["auth_reason_desc"] = AUTH_REASONS.get(
                        auth_reason, "unknown"
                    )
                elif "allowed" in record:
                    allowed = record["allowed"]
                    record["allowed_value"] = AUTH_VALUE_OLD.get(allowed, "unknown")

                if record.get("last_modified") is not None:
                    record["last_modified_value"] = record["last_modified"]
                    record["last_modified"] = convert_unix_to_iso(
                        record["last_modified"]
                    )
                if record.get("last_reminded") is not None:
                    record["last_reminded_value"] = record["last_reminded"]
                    record["last_reminded"] = convert_unix_to_iso(
                        record["last_reminded"]
                    )

                self.results.append(record)
        finally:
            cur.close()
            conn.close()

    def run(self) -> None:
        self._find_ios_database(backup_ids=TCC_BACKUP_IDS, root_paths=TCC_ROOT_PATHS)
        self.log.info("Found TCC database at path: %s", self.file_path)

        self.process_db(self.file_path)

        self.log.info("Extracted a total of %d TCC items", len(self.results))
