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
        assert dpa.results[0]["first_install_time"] == "2008-12-31 16:00:00"
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

    def test_per_user_fields_use_primary_user(self):
        details = DumpsysPackagesArtifact.parse_dumpsys_package_for_details(
            """    User 0: installed=true
      firstInstallTime=2024-01-10 09:19:39
      runtime permissions:
        android.permission.CAMERA: granted=true
    User 95: installed=false
      firstInstallTime=1970-01-01 01:00:00
      runtime permissions:
        android.permission.CAMERA: granted=false
        android.permission.RECORD_AUDIO: granted=false
"""
        )

        assert details["first_install_time"] == "2024-01-10 09:19:39"
        runtime_permissions = [
            permission
            for permission in details["permissions"]
            if permission["type"] == "runtime"
        ]
        assert runtime_permissions == [
            {
                "name": "android.permission.CAMERA",
                "granted": True,
                "type": "runtime",
            }
        ]

    def test_per_user_fields_fall_back_when_user_zero_is_missing(self):
        details = DumpsysPackagesArtifact.parse_dumpsys_package_for_details(
            """    User 10: installed=true
      firstInstallTime=2024-02-10 09:19:39
      runtime permissions:
        android.permission.CAMERA: granted=true
"""
        )

        assert details["first_install_time"] == "2024-02-10 09:19:39"
        assert details["permissions"][-1]["name"] == "android.permission.CAMERA"
