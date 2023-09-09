# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
import logging

from mvt.android.artifacts.dumpsys_battery_daily import DumpsysBatteryDailyArtifact
from mvt.common.indicators import Indicators

from ..utils import get_artifact


class TestDumpsysBatteryDailyArtifact:
    def test_parsing(self):
        dba = DumpsysBatteryDailyArtifact()
        file = get_artifact("android_data/dumpsys_battery.txt")
        with open(file) as f:
            data = f.read()

        assert len(dba.results) == 0
        dba.parse(data)
        assert len(dba.results) == 3

    def test_ioc_check(self, indicator_file):
        dba = DumpsysBatteryDailyArtifact()
        file = get_artifact("android_data/dumpsys_battery.txt")
        with open(file) as f:
            data = f.read()
        dba.parse(data)

        ind = Indicators(log=logging.getLogger())
        ind.parse_stix2(indicator_file)
        ind.ioc_collections[0]["app_ids"].append("com.facebook.system")
        dba.indicators = ind
        assert len(dba.detected) == 0
        dba.check_indicators()
        assert len(dba.detected) == 1
