# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
import logging

from mvt.android.artifacts.dumpsys_battery_history import DumpsysBatteryHistoryArtifact
from mvt.common.indicators import Indicators

from ..utils import get_artifact


class TestDumpsysBatteryHistoryArtifact:
    def test_parsing(self):
        dba = DumpsysBatteryHistoryArtifact()
        file = get_artifact("android_data/dumpsys_battery.txt")
        with open(file) as f:
            data = f.read()

        assert len(dba.results) == 0
        dba.parse(data)
        assert len(dba.results) == 5
        assert dba.results[0]["package_name"] == "com.samsung.android.app.reminder"
        assert dba.results[1]["event"] == "end_job"
        assert dba.results[2]["event"] == "start_top"
        assert dba.results[2]["uid"] == "u0a280"
        assert dba.results[2]["package_name"] == "com.whatsapp"
        assert dba.results[3]["event"] == "end_top"
        assert dba.results[4]["package_name"] == "com.sec.android.app.launcher"

    def test_ioc_check(self, indicator_file):
        dba = DumpsysBatteryHistoryArtifact()
        file = get_artifact("android_data/dumpsys_battery.txt")
        with open(file) as f:
            data = f.read()
        dba.parse(data)

        ind = Indicators(log=logging.getLogger())
        ind.parse_stix2(indicator_file)
        ind.ioc_collections[0]["app_ids"].append("com.samsung.android.app.reminder")
        dba.indicators = ind
        assert len(dba.alertstore.alerts) == 0
        dba.check_indicators()
        assert len(dba.alertstore.alerts) == 2

    def test_parsing_absolute_timestamps(self):
        dba = DumpsysBatteryHistoryArtifact()
        dba.parse(
            """07-15 20:27:39.431 (2) 100 +job=u0a123:"com.example/.ExampleJob"
07-15 20:27:40.431 (2) 100 -job=u0a123:"com.example/.ExampleJob"
"""
        )

        assert len(dba.results) == 2
        assert dba.results[0] == {
            "time_elapsed": "07-15 20:27:39.431",
            "timestamp": "1900-07-15 20:27:39.431000",
            "event": "start_job",
            "uid": "u0a123",
            "package_name": "com.example",
            "service": "com.example/.ExampleJob",
        }
        assert dba.results[1]["event"] == "end_job"
        assert dba.results[1]["uid"] == "u0a123"

    def test_wake_lock_without_component_is_retained(self):
        dba = DumpsysBatteryHistoryArtifact()
        dba.parse(
            "Battery History:\n"
            "  0 (2) 100 RESET:TIME: 2025-09-05-01-04-52-139\n"
            '  +1s (2) 100 +running +wake_lock=1000:"*alarm*:TIME_TICK"\n'
            '  +2s (2) 100 +running +wake_lock=u0a1:"*walarm*:com.whatsapp.MessageHandler.LOGOUT_ACTION"\n'
            "\n"
        )

        assert [record["event"] for record in dba.results] == ["wake", "wake"]
        assert dba.results[0]["package_name"] is None
        assert dba.results[1]["package_name"] == "com.whatsapp"

    def test_decorated_sync_job_uses_component_package(self):
        dba = DumpsysBatteryHistoryArtifact()
        dba.parse('+1s (2) 100 +job=u0a1:"@SyncManager@gmail-ls/com.google:android"\n')

        assert dba.results[0]["package_name"] == "com.google"
