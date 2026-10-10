# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import sqlite3

from mvt.common.module import run_module
from mvt.ios.modules.mixed.contacts import Contacts


def test_contacts_preserves_complete_rows_and_people_without_values(tmp_path):
    db_path = tmp_path / "AddressBook.sqlitedb"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE ABPerson (
            ROWID INTEGER PRIMARY KEY, First TEXT, Middle TEXT, Last TEXT,
            Organization TEXT, Note TEXT
        );
        CREATE TABLE ABMultiValue (
            ROWID INTEGER PRIMARY KEY, record_id INTEGER, value TEXT,
            label INTEGER
        );
        INSERT INTO ABPerson VALUES (1, 'Alice', NULL, 'Example', NULL, 'note');
        INSERT INTO ABPerson VALUES (2, 'Bob', NULL, 'NoValue', NULL, 'retained');
        INSERT INTO ABMultiValue VALUES (10, 1, '+491234', 3);
        """
    )
    conn.close()

    module = Contacts(file_path=str(db_path))
    run_module(module)

    assert len(module.results) == 2
    alice = next(result for result in module.results if result["first"] == "Alice")
    bob = next(result for result in module.results if result["first"] == "Bob")
    assert alice["contact"]["person_Note"] == "note"
    assert alice["contact"]["multivalue_label"] == 3
    assert alice["First"] == "Alice"
    assert bob["value"] is None
    assert bob["contact"]["person_Note"] == "retained"
