# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional

from mvt.common.module_types import (
    ModuleAtomicResult,
    ModuleResults,
    ModuleSerializedResult,
)
from mvt.common.utils import convert_mactime_to_iso, sanitize_json_data

from ..base import IOSExtraction

CALENDAR_BACKUP_IDS = [
    "2041457d5fe04d39d0ab481178355df6781e6858",
]
CALENDAR_ROOT_PATHS = ["private/var/mobile/Library/Calendar/Calendar.sqlitedb"]


class Calendar(IOSExtraction):
    """This module extracts all calendar entries."""

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
        self.timestamps = [
            "start_date",
            "end_date",
            "last_modified",
            "creation_date",
            "participant_last_modified",
        ]

    def serialize(self, record: ModuleAtomicResult) -> ModuleSerializedResult:
        records = []
        for timestamp in self.timestamps:
            if timestamp not in record or not record[timestamp]:
                continue

            records.append(
                {
                    "timestamp": record[timestamp],
                    "module": self.__class__.__name__,
                    "event": timestamp,
                    "data": f"Calendar event {record['summary']} ({record['description']}) "
                    f"(invitation by {record['participant_email']})",
                }
            )
        return records

    def check_indicators(self) -> None:
        for result in self.results:
            if result["participant_email"] and self.indicators:
                ioc_match = self.indicators.check_email(result["participant_email"])
                if ioc_match:
                    self.alertstore.critical(
                        ioc_match.message, "", result, matched_indicator=ioc_match.ioc
                    )
                    continue

            # Custom check for Quadream exploit
            if result["summary"] == "Meeting" and result["description"] == "Notes":
                self.alertstore.high(
                    f"Potential Quadream exploit event identified: {result['uuid']}",
                    "",
                    result,
                )

    def _parse_calendar_db(self):
        """
        Parse the calendar database
        """
        conn = self._open_sqlite_db(self.file_path)
        cur = conn.cursor()
        try:
            cur.execute("PRAGMA table_info(CalendarItem);")
            calendar_columns = [row[1] for row in cur]
            cur.execute("PRAGMA table_info(Participant);")
            participant_columns = [row[1] for row in cur]
            selected = [
                f'c."{column}" AS "calendar_{column}"' for column in calendar_columns
            ] + [
                f'p."{column}" AS "participant_{column}"'
                for column in participant_columns
            ]
            cur.execute(
                f"SELECT {', '.join(selected)} FROM CalendarItem c "
                "LEFT JOIN Participant p ON p.ROWID = c.organizer_id;"
            )
            names = [description[0] for description in cur.description]
            for row in cur:
                raw = sanitize_json_data(dict(zip(names, row)))
                entry = {
                    "id": raw.get("calendar_ROWID"),
                    "summary": raw.get("calendar_summary"),
                    "description": raw.get("calendar_description"),
                    "all_day": raw.get("calendar_all_day"),
                    "calendar_id": raw.get("calendar_calendar_id"),
                    "organizer_id": raw.get("calendar_organizer_id"),
                    "url": raw.get("calendar_url"),
                    "external_id": raw.get("calendar_external_id"),
                    "external_mod_tag": raw.get("calendar_external_mod_tag"),
                    "unique_identifier": raw.get("calendar_unique_identifier"),
                    "hidden": raw.get("calendar_hidden"),
                    "uuid": raw.get("calendar_UUID"),
                    "action": raw.get("calendar_action"),
                    "created_by_id": raw.get("calendar_created_by_id"),
                    "participant_uuid": raw.get("participant_UUID"),
                    "participant_email": raw.get("participant_email"),
                    "participant_phone": raw.get("participant_phone_number"),
                    "participant_comment": raw.get("participant_comment"),
                    "record": raw,
                }
                timestamp_sources = {
                    "start_date": "calendar_start_date",
                    "end_date": "calendar_end_date",
                    "last_modified": "calendar_last_modified",
                    "creation_date": "calendar_creation_date",
                    "participant_last_modified": "participant_last_modified",
                }
                for output, source in timestamp_sources.items():
                    value = raw.get(source)
                    entry[output] = (
                        convert_mactime_to_iso(value)
                        if value is not None and not isinstance(value, str)
                        else value
                    )
                self.results.append(entry)
        finally:
            cur.close()
            conn.close()

    def run(self) -> None:
        self._find_ios_database(
            backup_ids=CALENDAR_BACKUP_IDS, root_paths=CALENDAR_ROOT_PATHS
        )
        self.log.info("Found calendar database at path: %s", self.file_path)

        self._parse_calendar_db()

        self.log.info("Extracted a total of %d calendar items", len(self.results))
