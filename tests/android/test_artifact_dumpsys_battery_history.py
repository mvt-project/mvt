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
        assert len(dba.detected) == 0
        dba.check_indicators()
        assert len(dba.detected) == 2
