# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
import logging

from mvt.android.artifacts.dumpsys_appops import DumpsysAppopsArtifact
from mvt.common.indicators import Indicators

from ..utils import get_artifact


class TestDumpsysAppopsArtifact:
    def test_parsing(self):
        da = DumpsysAppopsArtifact()
        da.log = logging
        file = get_artifact("android_data/dumpsys_appops.txt")
        with open(file) as f:
            data = f.read()

        assert len(da.results) == 0
        da.parse(data)
        assert len(da.results) == 13
        assert da.results[0]["package_name"] == "com.android.phone"
        assert da.results[0]["uid"] == "0"
        assert len(da.results[0]["permissions"]) == 1
        assert da.results[0]["permissions"][0]["name"] == "MANAGE_IPSEC_TUNNELS"
        assert da.results[0]["permissions"][0]["mode"] == "allow"
        assert da.results[6]["package_name"] == "com.sec.factory.camera"
        assert len(da.results[6]["permissions"][1]["entries"]) == 1
        assert len(da.results[11]["permissions"]) == 4
        wake_lock = next(
            permission
            for permission in da.results[11]["permissions"]
            if permission["name"] == "WAKE_LOCK"
        )
        assert wake_lock["entries"][0]["duration"] == "+126ms"

    def test_running_and_attribution_are_retained(self):
        da = DumpsysAppopsArtifact()
        da.parse(
            """  Uid 0:
    state=cch
    Package com.example:
      CAMERA (allow):
        camera=[
          Access: [fg-s] 2025-01-01 00:00:00.000 (-1s) duration=+2ms
        ]
      RECORD_AUDIO (allow):
          Running start at: +3s
"""
        )

        camera = da.results[0]["permissions"][0]["entries"][0]
        running = da.results[0]["permissions"][1]["entries"][0]
        assert camera["attribution"] == "camera"
        assert running["event"] == "running"
        assert running["relative_time"] == "+3s"

    def test_ioc_check(self, indicator_file):
        da = DumpsysAppopsArtifact()
        da.log = logging
        file = get_artifact("android_data/dumpsys_appops.txt")
        with open(file) as f:
            data = f.read()
        da.parse(data)

        ind = Indicators(log=logging.getLogger())
        ind.parse_stix2(indicator_file)
        ind.ioc_collections[0]["app_ids"].append("com.facebook.katana")
        da.indicators = ind
        assert len(da.alertstore.alerts) == 0

        da.check_indicators()
        detected_by_ioc = [
            alert
            for alert in da.alertstore.alerts
            if alert.matched_indicator is not None
        ]
        detected_by_permission_heuristic = [
            alert
            for alert in da.alertstore.alerts
            if all(
                [
                    perm["name"] == "REQUEST_INSTALL_PACKAGES"
                    for perm in alert.event["permissions"]
                ]
            )
        ]
        assert len(da.alertstore.alerts) == 3
        assert len(detected_by_ioc) == 1
        assert detected_by_ioc[0].matched_indicator is not None
        assert len(detected_by_permission_heuristic) == 2
