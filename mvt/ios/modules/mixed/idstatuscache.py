# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import collections
import logging
import plistlib

from mvt.common.utils import convert_mactime_to_unix, convert_timestamp_to_iso

from ..base import IOSExtraction

IDSTATUSCACHE_BACKUP_IDS = [
    "6b97989189901ceaa4e5be9b7f05fb584120e27b",
]
IDSTATUSCACHE_ROOT_PATHS = [
    "private/var/mobile/Library/Preferences/com.apple.identityservices.idstatuscache.plist",
    "private/var/mobile/Library/IdentityServices/idstatuscache.plist",
]


class IDStatusCache(IOSExtraction):
    """Extracts Apple Authentication information from idstatuscache.plist"""

    def __init__(self, file_path: str = None, target_path: str = None,
                 results_path: str = None, fast_mode: bool = False,
                 log: logging.Logger = None, results: list = []) -> None:
        super().__init__(file_path=file_path, target_path=target_path,
                         results_path=results_path, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record: dict) -> None:
        return {
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": "lookup",
            "data": f"Lookup of {record['user']} within {record['package']} (Status {record['idstatus']})"
        }

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            if result.get("user", "").startswith("mailto:"):
                email = result["user"][7:].strip("'")
                ioc = self.indicators.check_email(email)
                if ioc:
                    result["matched_indicator"] = ioc
                    self.detected.append(result)
                    continue

            if "\\x00\\x00" in result.get("user", ""):
                self.log.warning("Found an ID Status Cache entry with suspicious patterns: %s",
                                 result.get("user"))
                self.detected.append(result)

    def _extract_idstatuscache_entries(self, file_path):
        with open(file_path, "rb") as handle:
            file_plist = plistlib.load(handle)

        id_status_cache_entries = []
        for app in file_plist:
            if not isinstance(file_plist[app], dict):
                continue

            for entry in file_plist[app]:
                try:
                    lookup_date = file_plist[app][entry]["LookupDate"]
                    id_status = file_plist[app][entry]["IDStatus"]
                except KeyError:
                    continue

                id_status_cache_entries.append({
                    "package": app,
                    "user": entry.replace("\x00", "\\x00"),
                    "isodate": convert_timestamp_to_iso(convert_mactime_to_unix(lookup_date)),
                    "idstatus": id_status,
                })

        entry_counter = collections.Counter([entry["user"] for entry in id_status_cache_entries])
        for entry in id_status_cache_entries:
            # Add total count of occurrences to the status cache entry.
            entry["occurrences"] = entry_counter[entry["user"]]
            self.results.append(entry)

    def run(self) -> None:

        if self.is_backup:
            self._find_ios_database(backup_ids=IDSTATUSCACHE_BACKUP_IDS)
            self.log.info("Found IDStatusCache plist at path: %s", self.file_path)
            self._extract_idstatuscache_entries(self.file_path)
        elif self.is_fs_dump:
            for idstatuscache_path in self._get_fs_files_from_patterns(IDSTATUSCACHE_ROOT_PATHS):
                self.file_path = idstatuscache_path
                self.log.info("Found IDStatusCache plist at path: %s", self.file_path)
                self._extract_idstatuscache_entries(self.file_path)

        self.log.info("Extracted a total of %d ID Status Cache entries", len(self.results))
