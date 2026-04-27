# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
import logging

from mvt.android.artifacts.dumpsys_battery_daily import DumpsysBatteryDailyArtifact
from mvt.common.alerts import AlertLevel
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
        assert len(dba.alertstore.alerts) == 0
        dba.check_indicators()
        assert len(dba.alertstore.alerts) == 1

    def test_uninstall_and_downgrade_create_medium_alerts(self):
        dba = DumpsysBatteryDailyArtifact()
        dba.parse(
            """
  Daily from 2022-08-16-15-56-39 to 2022-08-17-01-15-45:
      Update com.example.app vers=10
      Update com.example.removed vers=0
  Daily from 2022-08-17-15-56-39 to 2022-08-18-01-15-45:
      Update com.example.app vers=9
"""
        )

        assert len(dba.results) == 3
        assert len(dba.alertstore.alerts) == 2

        uninstall_alert, downgrade_alert = dba.alertstore.alerts
        assert uninstall_alert.level == AlertLevel.MEDIUM
        assert uninstall_alert.message == (
            "Detected uninstall of package com.example.removed (vers 0)"
        )
        assert uninstall_alert.event_time == "2022-08-16"
        assert uninstall_alert.event["package_name"] == "com.example.removed"
        assert uninstall_alert.event["vers"] == "0"

        assert downgrade_alert.level == AlertLevel.MEDIUM
        assert downgrade_alert.message == (
            "Detected downgrade of package com.example.app from vers 10 to vers 9"
        )
        assert downgrade_alert.event_time == "2022-08-17"
        assert downgrade_alert.event["package_name"] == "com.example.app"
        assert downgrade_alert.event["action"] == "downgrade"
        assert downgrade_alert.event["previous_vers"] == "10"
