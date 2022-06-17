# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import plistlib

from mvt.common.utils import convert_timestamp_to_iso

from ..base import IOSExtraction

CONF_PROFILES_EVENTS_RELPATH = "Library/ConfigurationProfiles/MCProfileEvents.plist"


class ProfileEvents(IOSExtraction):
    """This module extracts events related to the installation of configuration
    profiles.


    """
    def __init__(self, file_path: str = None, target_path: str = None,
                 results_path: str = None, fast_mode: bool = False,
                 log: logging.Logger = None, results: list = []) -> None:
        super().__init__(file_path=file_path, target_path=target_path,
                         results_path=results_path, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record: dict) -> None:
        return {
            "timestamp": record.get("timestamp"),
            "module": self.__class__.__name__,
            "event": "profile_operation",
            "data": f"Process {record.get('process')} started operation {record.get('operation')} of profile {record.get('profile_id')}"
        }

    def run(self) -> None:
        for events_file in self._get_backup_files_from_manifest(relative_path=CONF_PROFILES_EVENTS_RELPATH):
            events_file_path = self._get_backup_file_from_id(events_file["file_id"])
            if not events_file_path:
                continue

            with open(events_file_path, "rb") as handle:
                events_plist = plistlib.load(handle)

            if "ProfileEvents" not in events_plist:
                continue

            for event in events_plist["ProfileEvents"]:
                key = list(event.keys())[0]
                self.log.info("On %s process \"%s\" started operation \"%s\" of profile \"%s\"",
                              event[key].get("timestamp"), event[key].get("process"),
                              event[key].get("operation"), key)

                self.results.append({
                    "profile_id": key,
                    "timestamp": convert_timestamp_to_iso(event[key].get("timestamp")),
                    "operation": event[key].get("operation"),
                    "process": event[key].get("process"),
                })

        self.log.info("Extracted %d profile events", len(self.results))
