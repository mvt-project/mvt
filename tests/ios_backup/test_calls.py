# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import sqlite3

from mvt.common.module import run_module
from mvt.ios.modules.mixed.calls import Calls


def test_calls_preserves_complete_source_record(tmp_path):
    db_path = tmp_path / "CallHistory.storedata"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE ZCALLRECORD (
            ZDATE REAL, ZDURATION REAL, ZLOCATION TEXT, ZADDRESS BLOB,
            ZSERVICE_PROVIDER TEXT, ZORIGINATED INTEGER, ZANSWERED INTEGER,
            ZMETADATA BLOB
        );
        """
    )
    conn.execute(
        "INSERT INTO ZCALLRECORD VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
        (700000000, 42, "Berlin", b"+491234", "carrier", 1, 0, b"\x00\xff"),
    )
    conn.commit()
    conn.close()

    module = Calls(file_path=str(db_path))
    run_module(module)

    assert len(module.results) == 1
    assert module.results[0]["number"] == "+491234"
    assert module.results[0]["call"]["ZORIGINATED"] == 1
    assert module.results[0]["call"]["ZANSWERED"] == 0
    assert module.results[0]["call"]["ZMETADATA"] == "AP8="
