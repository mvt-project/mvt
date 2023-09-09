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
        assert da.results[0]["permissions"][0]["access"] == "allow"
        assert da.results[6]["package_name"] == "com.sec.factory.camera"
        assert len(da.results[6]["permissions"][1]["entries"]) == 1
        assert len(da.results[11]["permissions"]) == 4

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
        assert len(da.detected) == 0
        da.check_indicators()
        assert len(da.detected) == 1
