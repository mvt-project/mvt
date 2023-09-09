# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
import logging

from mvt.android.artifacts.dumpsys_package_activities import (
    DumpsysPackageActivitiesArtifact,
)
from mvt.common.indicators import Indicators

from ..utils import get_artifact


class TestDumpsysPackageActivitiesArtifact:
    def test_parsing(self):
        dpa = DumpsysPackageActivitiesArtifact()
        file = get_artifact("android_data/dumpsys_packages.txt")
        with open(file) as f:
            data = f.read()

        assert len(dpa.results) == 0
        dpa.parse(data)
        assert len(dpa.results) == 4
        assert dpa.results[0]["package_name"] == "com.samsung.android.app.social"
        assert (
            dpa.results[0]["activity"]
            == "com.samsung.android.app.social/.feed.FeedsActivity"
        )

    def test_ioc_check(self, indicator_file):
        dpa = DumpsysPackageActivitiesArtifact()
        file = get_artifact("android_data/dumpsys_packages.txt")
        with open(file) as f:
            data = f.read()
        dpa.parse(data)

        ind = Indicators(log=logging.getLogger())
        ind.parse_stix2(indicator_file)
        ind.ioc_collections[0]["app_ids"].append("com.google.android.gms")
        dpa.indicators = ind
        assert len(dpa.detected) == 0
        dpa.check_indicators()
        assert len(dpa.detected) == 1
