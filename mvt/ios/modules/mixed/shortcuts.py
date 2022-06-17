# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import io
import itertools
import logging
import plistlib
import sqlite3

from mvt.common.utils import (check_for_links, convert_mactime_to_unix,
                              convert_timestamp_to_iso)

from ..base import IOSExtraction

SHORTCUT_BACKUP_IDS = [
    "5b4d0b44b5990f62b9f4d34ad8dc382bf0b01094",
]
SHORTCUT_ROOT_PATHS = [
    "private/var/mobile/Library/Shortcuts/Shortcuts.sqlite",
]


class Shortcuts(IOSExtraction):
    """This module extracts all info about SMS/iMessage attachments."""

    def __init__(self, file_path: str = None, target_path: str = None,
                 results_path: str = None, fast_mode: bool = False,
                 log: logging.Logger = None, results: list = []) -> None:
        super().__init__(file_path=file_path, target_path=target_path,
                         results_path=results_path, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record: dict) -> None:
        found_urls = ""
        if record["action_urls"]:
            found_urls = "- URLs in actions: {}".format(", ".join(record["action_urls"]))
        desc = ""
        if record["description"]:
            desc = record["description"].decode('utf-8', errors='ignore')

        return [{
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": "shortcut_created",
            "data": f"iOS Shortcut '{record['shortcut_name'].decode('utf-8')}': {desc} {found_urls}"
        }, {
            "timestamp": record["modified_date"],
            "module": self.__class__.__name__,
            "event": "shortcut_modified",
            "data": f"iOS Shortcut '{record['shortcut_name'].decode('utf-8')}': {desc} {found_urls}"
        }]

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_domains(result["action_urls"])
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)

    def run(self) -> None:
        self._find_ios_database(backup_ids=SHORTCUT_BACKUP_IDS,
                                root_paths=SHORTCUT_ROOT_PATHS)
        self.log.info("Found Shortcuts database at path: %s", self.file_path)

        conn = sqlite3.connect(self.file_path)
        conn.text_factory = bytes
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT
                    ZSHORTCUT.Z_PK as "shortcut_id",
                    ZSHORTCUT.ZNAME as "shortcut_name",
                    ZSHORTCUT.ZCREATIONDATE as "created_date",
                    ZSHORTCUT.ZMODIFICATIONDATE as "modified_date",
                    ZSHORTCUT.ZACTIONSDESCRIPTION as "description",
                    ZSHORTCUTACTIONS.ZDATA as "action_data"
                FROM ZSHORTCUT
                LEFT JOIN ZSHORTCUTACTIONS ON ZSHORTCUTACTIONS.ZSHORTCUT == ZSHORTCUT.Z_PK;
            """)
        except sqlite3.OperationalError:
            # Table ZSHORTCUT does not exist
            self.log.info("Invalid shortcut database format, skipping...")
            cur.close()
            conn.close()
            return

        names = [description[0] for description in cur.description]

        for item in cur:
            shortcut = {}
            # We store the value of each column under the proper key.
            for index, value in enumerate(item):
                shortcut[names[index]] = value

            action_data = plistlib.load(io.BytesIO(shortcut.pop("action_data", [])))
            actions = []
            for action_entry in action_data:
                action = {}
                action["identifier"] = action_entry["WFWorkflowActionIdentifier"]
                action["parameters"] = action_entry["WFWorkflowActionParameters"]

                # URLs might be in multiple fields, do a simple regex search across the parameters.
                extracted_urls = check_for_links(str(action["parameters"]))

                # Remove quoting characters that may have been captured by the regex.
                action["urls"] = [url.rstrip("',") for url in extracted_urls]
                actions.append(action)

            shortcut["isodate"] = convert_timestamp_to_iso(convert_mactime_to_unix(shortcut.pop("created_date")))
            shortcut["modified_date"] = convert_timestamp_to_iso(convert_mactime_to_unix(shortcut["modified_date"]))
            shortcut["parsed_actions"] = len(actions)
            shortcut["action_urls"] = list(itertools.chain(*[action["urls"] for action in actions]))
            self.results.append(shortcut)

        cur.close()
        conn.close()

        self.log.info("Extracted a total of %d Shortcuts", len(self.results))
