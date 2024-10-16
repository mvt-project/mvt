# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional, Union

from mvt.common.utils import convert_mactime_to_iso

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
        self.timestamps = [
            "start_date",
            "end_date",
            "last_modified",
            "creation_date",
            "participant_last_modified",
        ]

    def serialize(self, record: dict) -> Union[dict, list]:
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
                ioc = self.indicators.check_email(result["participant_email"])
                if ioc:
                    result["matched_indicator"] = ioc
                    self.detected.append(result)
                    continue

            # Custom check for Quadream exploit
            if result["summary"] == "Meeting" and result["description"] == "Notes":
                self.log.warning(
                    "Potential Quadream exploit event identified: %s", result["uuid"]
                )
                self.detected.append(result)

    def _parse_calendar_db(self):
        """
        Parse the calendar database
        """
        conn = self._open_sqlite_db(self.file_path)
        cur = conn.cursor()

        cur.execute(
            """
        SELECT
            CalendarItem.ROWID as "id",
            CalendarItem.summary as "summary",
            CalendarItem.description as "description",
            CalendarItem.start_date as "start_date",
            CalendarItem.end_date as "end_date",
            CalendarItem.all_day as "all_day",
            CalendarItem.calendar_id as "calendar_id",
            CalendarItem.organizer_id as "organizer_id",
            CalendarItem.url as "url",
            CalendarItem.last_modified as "last_modified",
            CalendarItem.external_id as "external_id",
            CalendarItem.external_mod_tag as "external_mod_tag",
            CalendarItem.unique_identifier as "unique_identifier",
            CalendarItem.hidden as "hidden",
            CalendarItem.UUID as "uuid",
            CalendarItem.creation_date as "creation_date",
            CalendarItem.action as "action",
            CalendarItem.created_by_id as "created_by_id",
            Participant.UUID as "participant_uuid",
            Participant.email as "participant_email",
            Participant.phone_number as "participant_phone",
            Participant.comment as "participant_comment",
            Participant.last_modified as "participant_last_modified"
        FROM CalendarItem
            LEFT JOIN Participant ON Participant.ROWID = CalendarItem.organizer_id;
        """
        )

        names = [description[0] for description in cur.description]
        for item in cur:
            entry = {}
            for index, value in enumerate(item):
                if names[index] in self.timestamps:
                    if value is None or isinstance(value, str):
                        entry[names[index]] = value
                    else:
                        entry[names[index]] = convert_mactime_to_iso(value)
                else:
                    entry[names[index]] = value

            self.results.append(entry)

        cur.close()
        conn.close()

    def run(self) -> None:
        self._find_ios_database(
            backup_ids=CALENDAR_BACKUP_IDS, root_paths=CALENDAR_ROOT_PATHS
        )
        self.log.info("Found calendar database at path: %s", self.file_path)

        self._parse_calendar_db()

        self.log.info("Extracted a total of %d calendar items", len(self.results))
