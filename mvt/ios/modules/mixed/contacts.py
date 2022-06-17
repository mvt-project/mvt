# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import sqlite3

from ..base import IOSExtraction

CONTACTS_BACKUP_IDS = [
    "31bb7ba8914766d4ba40d6dfb6113c8b614be442",
]
CONTACTS_ROOT_PATHS = [
    "private/var/mobile/Library/AddressBook/AddressBook.sqlitedb",
]


class Contacts(IOSExtraction):
    """This module extracts all contact details from the phone's address book."""

    def __init__(self, file_path: str = None, target_path: str = None,
                 results_path: str = None, fast_mode: bool = False,
                 log: logging.Logger = None, results: list = []) -> None:
        super().__init__(file_path=file_path, target_path=target_path,
                         results_path=results_path, fast_mode=fast_mode,
                         log=log, results=results)

    def run(self) -> None:
        self._find_ios_database(backup_ids=CONTACTS_BACKUP_IDS, root_paths=CONTACTS_ROOT_PATHS)
        self.log.info("Found Contacts database at path: %s", self.file_path)

        conn = sqlite3.connect(self.file_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT
                multi.value, person.first, person.middle, person.last,
                person.organization
            FROM ABPerson person, ABMultiValue multi
            WHERE person.rowid = multi.record_id and multi.value not null
            ORDER by person.rowid ASC;
        """)
        names = [description[0] for description in cur.description]

        for row in cur:
            new_contact = {}
            for index, value in enumerate(row):
                new_contact[names[index]] = value

            self.results.append(new_contact)

        cur.close()
        conn.close()

        self.log.info("Extracted a total of %d contacts from the address book",
                      len(self.results))
