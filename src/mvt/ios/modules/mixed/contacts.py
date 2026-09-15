# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import sqlite3
from typing import Optional

from mvt.common.module_types import ModuleResults
from mvt.common.utils import sanitize_json_data

from ..base import IOSExtraction

CONTACTS_BACKUP_IDS = [
    "31bb7ba8914766d4ba40d6dfb6113c8b614be442",
]
CONTACTS_ROOT_PATHS = [
    "private/var/mobile/Library/AddressBook/AddressBook.sqlitedb",
]


class Contacts(IOSExtraction):
    """This module extracts all contact details from the phone's address book."""

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

    def run(self) -> None:
        self._find_ios_database(
            backup_ids=CONTACTS_BACKUP_IDS, root_paths=CONTACTS_ROOT_PATHS
        )
        self.log.info("Found Contacts database at path: %s", self.file_path)

        if not self.file_path:
            return
        conn = self._open_sqlite_db(self.file_path)
        cur = conn.cursor()
        try:
            cur.execute("PRAGMA table_info(ABPerson);")
            person_columns = [row[1] for row in cur]
            cur.execute("PRAGMA table_info(ABMultiValue);")
            multivalue_columns = [row[1] for row in cur]
            if not person_columns or not multivalue_columns:
                return

            select_columns = [
                f'p."{column}" AS "person_{column}"' for column in person_columns
            ] + [
                f'm."{column}" AS "multivalue_{column}"'
                for column in multivalue_columns
            ]
            cur.execute(
                f"SELECT {', '.join(select_columns)} "
                "FROM ABPerson p LEFT JOIN ABMultiValue m "
                "ON p.ROWID = m.record_id ORDER BY p.ROWID, m.ROWID;"
            )
            names = [description[0] for description in cur.description]
            for row in cur:
                raw = sanitize_json_data(dict(zip(names, row)))
                self.results.append(
                    {
                        "value": raw.get("multivalue_value"),
                        "first": raw.get("person_First"),
                        "middle": raw.get("person_Middle"),
                        "last": raw.get("person_Last"),
                        "organization": raw.get("person_Organization"),
                        # Keep the capitalization returned by the previous
                        # query for consumers of existing JSON output.
                        "First": raw.get("person_First"),
                        "Middle": raw.get("person_Middle"),
                        "Last": raw.get("person_Last"),
                        "Organization": raw.get("person_Organization"),
                        "contact": raw,
                    }
                )
        except sqlite3.OperationalError as exc:
            self.log.info("Error while reading the contact table: %s", exc)
        finally:
            cur.close()
            conn.close()

        self.log.info(
            "Extracted a total of %d contacts from the address book", len(self.results)
        )
