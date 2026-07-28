# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import hashlib
import os
import plistlib
import shutil
import sqlite3

from mvt.ios.modules.base import IOSExtraction
from mvt.ios.modules.fs.analytics import Analytics


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_open_sqlite_reads_wal_without_modifying_evidence(tmp_path):
    live_path = tmp_path / "live.db"
    evidence_path = tmp_path / "evidence.db"
    conn = sqlite3.connect(live_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA wal_autocheckpoint=0;")
    conn.execute("CREATE TABLE records (value TEXT);")
    conn.commit()
    conn.execute("INSERT INTO records VALUES ('from wal');")
    conn.commit()

    shutil.copy2(live_path, evidence_path)
    shutil.copy2(str(live_path) + "-wal", str(evidence_path) + "-wal")
    conn.close()

    evidence_hash = _sha256(evidence_path)
    wal_hash = _sha256(tmp_path / "evidence.db-wal")
    module = IOSExtraction(file_path=str(evidence_path))
    read_conn = module._open_sqlite_db(str(evidence_path))
    rows = read_conn.execute("SELECT value FROM records;").fetchall()
    read_conn.close()

    assert rows == [("from wal",)]
    assert _sha256(evidence_path) == evidence_hash
    assert _sha256(tmp_path / "evidence.db-wal") == wal_hash
    assert not os.path.exists(str(evidence_path) + "-shm")


def test_recovery_preserves_source_database(tmp_path):
    database_path = tmp_path / "source.db"
    conn = sqlite3.connect(database_path)
    conn.execute("CREATE TABLE records (value TEXT);")
    conn.execute("INSERT INTO records VALUES ('preserved');")
    conn.commit()
    conn.close()
    source_hash = _sha256(database_path)

    module = IOSExtraction(file_path=str(database_path))
    module._recover_sqlite_db_if_needed(str(database_path), forced=True)
    recovered_conn = module._open_sqlite_db(str(database_path))
    rows = recovered_conn.execute("SELECT value FROM records;").fetchall()
    recovered_conn.close()

    assert rows == [("preserved",)]
    assert _sha256(database_path) == source_hash
    assert not os.path.exists(str(database_path) + ".bak")


def test_analytics_skips_empty_rows_and_continues(tmp_path):
    database_path = tmp_path / "analytics.db"
    conn = sqlite3.connect(database_path)
    for table in ("hard_failures", "soft_failures", "all_events"):
        conn.execute(f"CREATE TABLE {table} (timestamp REAL, data BLOB);")
    conn.execute("INSERT INTO hard_failures VALUES (NULL, NULL);")
    conn.execute(
        "INSERT INTO soft_failures VALUES (?, ?);",
        (1.0, plistlib.dumps({"event": "valid"})),
    )
    conn.commit()
    conn.close()

    module = Analytics(file_path=str(database_path))
    module._extract_analytics_data()

    assert len(module.results) == 1
    assert module.results[0]["event"] == "valid"
