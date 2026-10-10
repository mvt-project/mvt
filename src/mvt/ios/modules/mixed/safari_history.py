# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
from typing import Optional

from mvt.common.module_types import (
    ModuleAtomicResult,
    ModuleResults,
    ModuleSerializedResult,
)
from mvt.common.url import URL
from mvt.common.utils import (
    convert_mactime_to_datetime,
    convert_mactime_to_iso,
    sanitize_json_data,
)

from ..base import IOSExtraction

# Safari profiles (iOS 17 and later) each keep their own History.db under
# Library/Safari/Profiles/<UUID>/, separate from the default profile's database.
SAFARI_HISTORY_BACKUP_RELPATHS = [
    "Library/Safari/History.db",
    "Library/Safari/Profiles/*/History.db",
]
SAFARI_HISTORY_ROOT_PATHS = [
    "private/var/mobile/Library/Safari/History.db",
    "private/var/mobile/Library/Safari/Profiles/*/History.db",
    "private/var/mobile/Containers/Data/Application/*/Library/Safari/History.db",
    "private/var/mobile/Containers/Data/Application/*/Library/Safari/Profiles/*/History.db",
]


class SafariHistory(IOSExtraction):
    """This module extracts all Safari visits and tries to detect potential
    network injection attacks.


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

    def serialize(self, record: ModuleAtomicResult) -> ModuleSerializedResult:
        return {
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": "safari_history",
            "data": f"Safari visit to {record['url']} (ID: {record['id']}, "
            f"Visit ID: {record['visit_id']})",
        }

    def _find_injections(self):
        for result in self.results:
            # We presume injections only happen on HTTP visits.
            if not result["url"].lower().startswith("http://"):
                continue

            # If there is no destination, no redirect happened.
            if not result["redirect_destination"]:
                continue

            try:
                origin_domain = URL(result["url"]).domain
            except Exception:
                origin_domain = ""

            # We loop again through visits in order to find redirect record.
            for redirect in self.results:
                if redirect["safari_history_db"] != result["safari_history_db"]:
                    continue

                if redirect["visit_id"] != result["redirect_destination"]:
                    continue

                try:
                    redirect_domain = URL(redirect["url"]).domain
                except Exception:
                    redirect_domain = ""

                # If the redirect destination is the same domain as the origin,
                # it's most likely an HTTPS upgrade.
                if origin_domain == redirect_domain:
                    continue

                self.log.info(
                    'Found HTTP redirect to different domain: "%s" -> "%s"',
                    origin_domain,
                    redirect_domain,
                )

                redirect_time = convert_mactime_to_datetime(redirect["timestamp"])
                origin_time = convert_mactime_to_datetime(result["timestamp"])
                elapsed_time = redirect_time - origin_time
                elapsed_ms = elapsed_time.microseconds / 1000

                if elapsed_time.seconds == 0:
                    self.alertstore.medium(
                        f"Redirect took less than a second! ({elapsed_ms} milliseconds)",
                        convert_mactime_to_iso(result["timestamp"]),
                        result,
                    )

    def check_indicators(self) -> None:
        self._find_injections()

        if not self.indicators:
            return

        for result in self.results:
            ioc_match = self.indicators.check_url(result["url"])
            if ioc_match:
                self.alertstore.critical(
                    ioc_match.message, "", result, matched_indicator=ioc_match.ioc
                )

    def _process_history_db(self, history_path):
        self._recover_sqlite_db_if_needed(history_path)
        conn = self._open_sqlite_db(history_path)
        cur = conn.cursor()
        try:
            cur.execute("PRAGMA table_info(history_items);")
            item_columns = [row[1] for row in cur]
            cur.execute("PRAGMA table_info(history_visits);")
            visit_columns = [row[1] for row in cur]
            selected = [
                f'i."{column}" AS "item_{column}"' for column in item_columns
            ] + [f'v."{column}" AS "visit_{column}"' for column in visit_columns]
            cur.execute(
                f"SELECT {', '.join(selected)} FROM history_items i "
                "JOIN history_visits v ON v.history_item = i.id "
                "ORDER BY v.visit_time;"
            )
            names = [description[0] for description in cur.description]
            for row in cur:
                raw = sanitize_json_data(dict(zip(names, row)))
                timestamp = raw.get("visit_visit_time")
                self.results.append(
                    {
                        "id": raw.get("item_id"),
                        "url": raw.get("item_url"),
                        "visit_id": raw.get("visit_id"),
                        "timestamp": timestamp,
                        "isodate": convert_mactime_to_iso(timestamp),
                        "redirect_source": raw.get("visit_redirect_source"),
                        "redirect_destination": raw.get("visit_redirect_destination"),
                        "safari_history_db": os.path.relpath(
                            history_path, self.target_path
                        ),
                        "record": raw,
                    }
                )
        finally:
            cur.close()
            conn.close()

    def run(self) -> None:
        if self.is_backup:
            for relative_path in SAFARI_HISTORY_BACKUP_RELPATHS:
                for history_file in self._get_backup_files_from_manifest(
                    relative_path=relative_path
                ):
                    history_path = self._get_backup_file_from_id(
                        history_file["file_id"]
                    )

                    if not history_path:
                        continue

                    self.log.info(
                        "Found Safari history database at path: %s", history_path
                    )

                    self._process_history_db(history_path)
        elif self.is_fs_dump:
            for history_path in self._get_fs_files_from_patterns(
                SAFARI_HISTORY_ROOT_PATHS
            ):
                self.log.info("Found Safari history database at path: %s", history_path)
                self._process_history_db(history_path)

        self.log.info("Extracted a total of %d history records", len(self.results))
