# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional

from mvt.common.module_types import ModuleAtomicResult, ModuleSerializedResult
from mvt.common.utils import convert_mactime_to_iso

from ..base import IOSExtraction

CALLS_BACKUP_IDS = [
    "5a4935c78a5255723f707230a451d79c540d2741",
]
CALLS_ROOT_PATHS = ["private/var/mobile/Library/CallHistoryDB/CallHistory.storedata"]


class Calls(IOSExtraction):
    """This module extracts phone calls details"""

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

    def serialize(self, record: ModuleAtomicResult) -> ModuleSerializedResult:
        return {
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": "call",
            "data": f"From {record['number']} using {record['provider']} "
            f"during {record['duration']} seconds",
        }

    def run(self) -> None:
        self._find_ios_database(
            backup_ids=CALLS_BACKUP_IDS, root_paths=CALLS_ROOT_PATHS
        )
        self.log.info("Found Calls database at path: %s", self.file_path)

        if not self.file_path:
            return
        conn = self._open_sqlite_db(self.file_path)
        cur = conn.cursor()
        try:
            cur.execute("PRAGMA table_info(ZCALLRECORD);")
            columns = {column[1].upper() for column in cur}
            originated_column = "ZORIGINATED" if "ZORIGINATED" in columns else "NULL"
            answered_column = "ZANSWERED" if "ZANSWERED" in columns else "NULL"
            cur.execute(
                f"""
                SELECT
                    ZDATE, ZDURATION, ZLOCATION, ZADDRESS, ZSERVICE_PROVIDER,
                    {originated_column}, {answered_column}
                FROM ZCALLRECORD;
                """
            )

            for (
                date,
                duration,
                location,
                address,
                provider,
                originated,
                answered,
            ) in cur:
                self.results.append(
                    {
                        "isodate": convert_mactime_to_iso(date),
                        "duration": duration,
                        "location": location,
                        "number": (
                            address.decode("utf-8")
                            if isinstance(address, bytes)
                            else address
                        ),
                        "provider": provider,
                        "originated": originated,
                        "answered": answered,
                    }
                )
        finally:
            cur.close()
            conn.close()

        self.log.info("Extracted a total of %d calls", len(self.results))
