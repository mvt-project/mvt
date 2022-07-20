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
            "data": f"Process {record.get('process')} started operation " \
                    f"{record.get('operation')} of profile {record.get('profile_id')}"
        }

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_process(result.get("process"))
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)
                continue

            ioc = self.indicators.check_profile(result.get("profile_id"))
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)

    @staticmethod
    def parse_profile_events(file_data: bytes) -> list:
        results = []

        events_plist = plistlib.loads(file_data)

        if "ProfileEvents" not in events_plist:
            return results

        for event in events_plist["ProfileEvents"]:
            key = list(event.keys())[0]

            result = {
                "profile_id": key,
                "timestamp": "",
                "operation": "",
                "process": "",
            }

            for key, value in event[key].items():
                key = key.lower()
                if key == "timestamp":
                    result["timestamp"] = str(convert_timestamp_to_iso(value))
                else:
                    result[key] = value

            results.append(result)

        return results

    def run(self) -> None:
        for events_file in self._get_backup_files_from_manifest(relative_path=CONF_PROFILES_EVENTS_RELPATH):
            events_file_path = self._get_backup_file_from_id(events_file["file_id"])
            if not events_file_path:
                continue

            self.log.info("Found MCProfileEvents.plist file at %s", events_file_path)

            with open(events_file_path, "rb") as handle:
                self.results.extend(self.parse_profile_events(handle.read()))

        for result in self.results:
            self.log.info("On %s process \"%s\" started operation \"%s\" of profile \"%s\"",
                          result.get("timestamp"), result.get("process"),
                          result.get("operation"), result.get("profile_id"))

        self.log.info("Extracted %d profile events", len(self.results))
