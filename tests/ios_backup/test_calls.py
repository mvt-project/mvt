# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import sqlite3

import pytest

from mvt.common.module import run_module
from mvt.ios.modules.mixed.calls import Calls


@pytest.mark.parametrize("has_flags", [True, False])
def test_calls_reads_optional_call_flags(tmp_path, has_flags):
    db_path = tmp_path / "CallHistory.storedata"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE ZCALLRECORD (
                ZDATE REAL, ZDURATION REAL, ZLOCATION TEXT, ZADDRESS BLOB,
                ZSERVICE_PROVIDER TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO ZCALLRECORD VALUES (?, ?, ?, ?, ?)",
            (700000000, 42, "Berlin", b"+491234", "carrier"),
        )
        if has_flags:
            conn.execute("ALTER TABLE ZCALLRECORD ADD COLUMN ZORIGINATED INTEGER")
            conn.execute("ALTER TABLE ZCALLRECORD ADD COLUMN ZANSWERED INTEGER")
            conn.execute("UPDATE ZCALLRECORD SET ZORIGINATED = 1, ZANSWERED = 0")
        conn.commit()
    finally:
        conn.close()

    module = Calls(file_path=str(db_path))
    run_module(module)

    assert len(module.results) == 1
    record = module.results[0]
    assert record["number"] == "+491234"
    assert record["originated"] == (1 if has_flags else None)
    assert record["answered"] == (0 if has_flags else None)
