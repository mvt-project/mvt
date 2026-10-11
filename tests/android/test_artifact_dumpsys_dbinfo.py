# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
import logging

from mvt.android.artifacts.dumpsys_dbinfo import DumpsysDBInfoArtifact
from mvt.common.indicators import Indicators

from ..utils import get_artifact


class TestDumpsysDBinfoArtifact:
    def test_parsing(self):
        dbi = DumpsysDBInfoArtifact()
        file = get_artifact("android_data/dumpsys_dbinfo.txt")
        with open(file) as f:
            data = f.read()

        assert len(dbi.results) == 0
        dbi.parse(data)
        assert len(dbi.results) == 5
        assert dbi.results[0]["action"] == "executeForCursorWindow"
        assert dbi.results[0]["sql"] == "PRAGMA database_list;"
        assert (
            dbi.results[0]["path"] == "/data/user/0/com.wssyncmldm/databases/idmsdk.db"
        )

    def test_ioc_check(self, indicator_file):
        dbi = DumpsysDBInfoArtifact()
        file = get_artifact("android_data/dumpsys_dbinfo.txt")
        with open(file) as f:
            data = f.read()
        dbi.parse(data)

        ind = Indicators(log=logging.getLogger())
        ind.parse_stix2(indicator_file)
        ind.ioc_collections[0]["app_ids"].append("com.wssyncmldm")
        dbi.indicators = ind
        assert len(dbi.alertstore.alerts) == 0
        dbi.check_indicators()
        assert len(dbi.alertstore.alerts) == 5

    def test_parsing_month_day_timestamp_without_pid(self):
        dbi = DumpsysDBInfoArtifact()
        dbi.parse(
            """
Connection pool for /data/user/0/com.example/databases/current.db:
      Most recently executed operations:
        0: [07-15 20:27:39.431] executeForCursorWindow took 1ms - succeeded, sql="SELECT 1"
"""
        )

        assert dbi.results == [
            {
                "timestamp": "07-15 20:27:39.431",
                "pid": None,
                "action": "executeForCursorWindow",
                "duration_ms": 1,
                "status": "succeeded",
                "sql": "SELECT 1",
                "path": "/data/user/0/com.example/databases/current.db",
                "pool_path": "/data/user/0/com.example/databases/current.db",
                "connection_number": None,
                "is_primary": None,
            }
        ]

    def test_parses_operations_from_multiple_connections(self):
        dbi = DumpsysDBInfoArtifact()
        dbi.parse(
            """Connection pool for /data/example.db:
    Connection #0:
      isPrimaryConnection: true
      Most recently executed operations:
        0: [2025-01-01 00:00:00.000] execute took 1ms - succeeded, sql="SELECT 1", path=/data/example.db
    Connection #1:
      isPrimaryConnection: false
      Most recently executed operations:
        0: [2025-01-01 00:00:01.000] execute took 2ms - succeeded, sql="SELECT 2", path=/data/example.db
"""
        )

        assert [record["connection_number"] for record in dbi.results] == [0, 1]
