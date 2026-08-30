# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
import logging

from mvt.android.artifacts.dumpsys_packages import DumpsysPackagesArtifact
from mvt.common.indicators import Indicators

from ..utils import get_artifact


class TestDumpsysPackagesArtifact:
    def test_parsing(self):
        dpa = DumpsysPackagesArtifact()
        file = get_artifact("android_data/dumpsys_packages.txt")
        with open(file) as f:
            data = f.read()

        assert len(dpa.results) == 0
        dpa.parse(data)
        assert len(dpa.results) == 2
        assert (
            dpa.results[0]["package_name"]
            == "com.samsung.android.provider.filterprovider"
        )
        assert dpa.results[0]["version_name"] == "5.0.07"
        assert dpa.results[0]["version_code"] == 500700000
        assert dpa.results[0]["min_sdk"] == 28
        assert dpa.results[0]["target_sdk"] == 28
        assert dpa.results[0]["package_type"] == "active"
        assert dpa.results[0]["users"][0]["user_id"] == 0
        assert dpa.results[0]["system"] is True

    def test_parsing_system_flag(self):
        system_details = DumpsysPackagesArtifact.parse_dumpsys_package_for_details(
            "    pkgFlags=[ SYSTEM HAS_CODE ALLOW_CLEAR_USER_DATA ]"
        )
        third_party_details = DumpsysPackagesArtifact.parse_dumpsys_package_for_details(
            "    pkgFlags=[ HAS_CODE ALLOW_BACKUP ]"
        )
        missing_flag_details = (
            DumpsysPackagesArtifact.parse_dumpsys_package_for_details(
                "    versionName=1.0"
            )
        )

        assert system_details["system"] is True
        assert third_party_details["system"] is False
        assert missing_flag_details["system"] is False

    def test_ioc_check(self, indicator_file):
        dpa = DumpsysPackagesArtifact()
        file = get_artifact("android_data/dumpsys_packages.txt")
        with open(file) as f:
            data = f.read()
        dpa.parse(data)

        ind = Indicators(log=logging.getLogger())
        ind.parse_stix2(indicator_file)
        ind.ioc_collections[0]["app_ids"].append("com.sec.android.app.DataCreate")
        dpa.indicators = ind
        assert len(dpa.alertstore.alerts) == 0
        dpa.check_indicators()
        assert len(dpa.alertstore.alerts) == 1

    def test_hidden_packages_and_per_user_state(self):
        dpa = DumpsysPackagesArtifact()
        dpa.parse(
            """Packages:
  Package [com.example.active]:
    appId=10001
    versionCode=12 minSdk=29 targetSdk=35
    User 0: installed=true hidden=false
      firstInstallTime=2025-01-01 01:02:03
    User 10: installed=false hidden=true
      firstInstallTime=2025-01-02 01:02:03
Hidden system packages:
  Package [com.example.hidden]:
    appId=10002
    installerPackageName=null
"""
        )

        assert [record["package_type"] for record in dpa.results] == [
            "active",
            "hidden_system",
        ]
        assert len(dpa.results[0]["users"]) == 2
        assert dpa.results[1]["installer"] is None
