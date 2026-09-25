# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
import logging

from mvt.android.artifacts.dumpsys_accessibility import DumpsysAccessibilityArtifact
from mvt.common.alerts import AlertLevel
from mvt.common.indicators import Indicators

from ..utils import get_artifact


class TestDumpsysAccessibilityArtifact:
    def test_parsing(self):
        da = DumpsysAccessibilityArtifact()
        file = get_artifact("android_data/dumpsys_accessibility.txt")
        with open(file) as f:
            data = f.read()

        assert len(da.results) == 0
        da.parse(data)
        assert len(da.results) == 4
        assert da.results[0]["package_name"] == "com.android.settings"
        assert (
            da.results[0]["component"]
            == "com.android.settings/com.samsung.android.settings.development.gpuwatch.GPUWatchInterceptor"
        )

    def test_parsing_v14_aosp_format(self):
        da = DumpsysAccessibilityArtifact()
        file = get_artifact("android_data/dumpsys_accessibility_v14_or_later.txt")
        with open(file) as f:
            data = f.read()

        assert len(da.results) == 0
        da.parse(data)
        # One named service, plus one count-only record: the dump states
        # `installedServiceCount=2` and names only one component.
        assert len(da.results) == 2
        assert da.results[0]["package_name"] == "com.malware.accessibility"
        assert da.results[0]["service_name"] == "com.malware.service.malwareservice"
        assert da.results[0]["enabled"] is True
        # This fixture never prints an `installed services:` section, so the
        # dump does not state the installed status. Reporting False would turn
        # "not stated" into "not installed", so it reads None here.
        assert da.results[0]["installed"] is None

    def test_accessibility_service_alert(self):
        da = DumpsysAccessibilityArtifact()
        file = get_artifact("android_data/dumpsys_accessibility_v14_or_later.txt")
        with open(file) as f:
            data = f.read()
        da.parse(data)

        da.check_indicators()

        assert len(da.alertstore.alerts) == 2
        assert da.alertstore.alerts[0].level == AlertLevel.MEDIUM
        assert da.alertstore.alerts[0].event == da.results[0]
        assert da.alertstore.alerts[1].level == AlertLevel.LOW
        assert da.alertstore.alerts[1].event == da.results[1]

    def test_same_component_is_kept_for_each_user(self):
        da = DumpsysAccessibilityArtifact()
        da.parse(
            """User state[attributes:{id=0
  installed services: {
    0 : com.example/.Service
  }
User state[attributes:{id=10
  installed services: {
    0 : com.example/.Service
  }
"""
        )

        assert [result["user_id"] for result in da.results] == [0, 10]

    def test_ioc_check(self, indicator_file):
        da = DumpsysAccessibilityArtifact()
        file = get_artifact("android_data/dumpsys_accessibility.txt")
        with open(file) as f:
            data = f.read()
        da.parse(data)

        ind = Indicators(log=logging.getLogger())
        ind.parse_stix2(indicator_file)
        ind.ioc_collections[0]["app_ids"].append("com.sec.android.app.camera")
        da.indicators = ind
        assert len(da.alertstore.alerts) == 0
        da.check_indicators()
        assert len(da.alertstore.alerts) == len(da.results)
        # Every service in this fixture is installed and switched off
        # (`enabled services:{}` is printed and empty), so the three non-IOC
        # findings are LOW, not MEDIUM. The IOC match is unaffected by the
        # state.
        assert da.alertstore.count(AlertLevel.LOW) == 3
        assert da.alertstore.count(AlertLevel.CRITICAL) == 1
        critical_alert = next(
            alert
            for alert in da.alertstore.alerts
            if alert.level == AlertLevel.CRITICAL
        )
        assert critical_alert.event["package_name"] == "com.sec.android.app.camera"
