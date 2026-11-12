# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional

from mvt.common.module_types import ModuleResults
from mvt.common.utils import convert_mactime_to_iso, sanitize_json_data

from ..net_base import NetBase

DATAUSAGE_BACKUP_IDS = [
    "0d609c54856a9bb2d56729df1d68f2958a88426b",
]
DATAUSAGE_ROOT_PATHS = [
    "private/var/wireless/Library/Databases/DataUsage.sqlite",
]


class Datausage(NetBase):
    """This class extracts data from DataUsage.sqlite and attempts to identify
    any suspicious processes if running on a full filesystem dump.


    """

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

    def _extract_net_data(self):
        assert self.file_path is not None
        conn = self._open_sqlite_db(self.file_path)
        cur = conn.cursor()
        try:
            cur.execute("PRAGMA table_info(ZPROCESS);")
            process_columns = [row[1] for row in cur]
            cur.execute("PRAGMA table_info(ZLIVEUSAGE);")
            live_columns = [row[1] for row in cur]
            selected = [
                f'p."{column}" AS "process_{column}"' for column in process_columns
            ] + [f'l."{column}" AS "live_{column}"' for column in live_columns]
            cur.execute(
                f"SELECT {', '.join(selected)} FROM ZLIVEUSAGE l "
                "LEFT JOIN ZPROCESS p ON l.ZHASPROCESS = p.Z_PK;"
            )
            names = [description[0] for description in cur.description]
            rows = [dict(zip(names, row)) for row in cur]

            process_only = [
                f'p."{column}" AS "process_{column}"' for column in process_columns
            ] + [f'NULL AS "live_{column}"' for column in live_columns]
            cur.execute(
                f"SELECT {', '.join(process_only)} FROM ZPROCESS p "
                "WHERE NOT EXISTS ("
                "SELECT 1 FROM ZLIVEUSAGE l WHERE l.ZHASPROCESS = p.Z_PK);"
            )
            names = [description[0] for description in cur.description]
            rows.extend(dict(zip(names, row)) for row in cur)
        finally:
            cur.close()
            conn.close()

        for raw_row in rows:
            first_timestamp = raw_row.get("process_ZFIRSTTIMESTAMP")
            process_timestamp = raw_row.get("process_ZTIMESTAMP")
            live_timestamp = raw_row.get("live_ZTIMESTAMP")
            first_isodate = (
                convert_mactime_to_iso(first_timestamp)
                if first_timestamp
                else first_timestamp
            )
            isodate = (
                convert_mactime_to_iso(process_timestamp)
                if process_timestamp
                else process_timestamp
            )
            live_isodate = (
                convert_mactime_to_iso(live_timestamp)
                if live_timestamp
                else first_isodate
            )
            self.results.append(
                {
                    "first_isodate": first_isodate,
                    "isodate": isodate,
                    "proc_name": raw_row.get("process_ZPROCNAME"),
                    "bundle_id": raw_row.get("process_ZBUNDLENAME"),
                    "proc_id": raw_row.get("process_Z_PK"),
                    "wifi_in": raw_row.get("live_ZWIFIIN"),
                    "wifi_out": raw_row.get("live_ZWIFIOUT"),
                    "wwan_in": raw_row.get("live_ZWWANIN"),
                    "wwan_out": raw_row.get("live_ZWWANOUT"),
                    "live_id": raw_row.get("live_Z_PK"),
                    "live_proc_id": raw_row.get("live_ZHASPROCESS"),
                    "live_isodate": live_isodate,
                    "record": sanitize_json_data(raw_row),
                }
            )
        self.log.info("Extracted information on %d processes", len(self.results))

    def run(self) -> None:
        self._find_ios_database(
            backup_ids=DATAUSAGE_BACKUP_IDS, root_paths=DATAUSAGE_ROOT_PATHS
        )
        self.log.info("Found DataUsage database at path: %s", self.file_path)

        self._extract_net_data()
        self._find_suspicious_processes()
