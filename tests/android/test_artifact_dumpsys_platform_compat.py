# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
import logging

from mvt.android.artifacts.dumpsys_platform_compat import DumpsysPlatformCompatArtifact
from mvt.common.indicators import Indicators

from ..utils import get_artifact


class TestDumpsysPlatformCompatArtifact:
    def test_parsing(self):
        dbi = DumpsysPlatformCompatArtifact()
        file = get_artifact("android_data/dumpsys_platform_compat.txt")
        with open(file) as f:
            data = f.read()

        assert len(dbi.results) == 0
        dbi.parse(data)
        assert len(dbi.results) == 2
        assert dbi.results[0]["package_name"] == "org.torproject.torbrowser"
        assert dbi.results[1]["package_name"] == "org.article19.circulo.next"

    def test_ioc_check(self, indicator_file):
        dbi = DumpsysPlatformCompatArtifact()
        file = get_artifact("android_data/dumpsys_platform_compat.txt")
        with open(file) as f:
            data = f.read()
        dbi.parse(data)

        ind = Indicators(log=logging.getLogger())
        ind.parse_stix2(indicator_file)
        ind.ioc_collections[0]["app_ids"].append("org.torproject.torbrowser")
        ind.ioc_collections[0]["app_ids"].append("org.article19.circulo.next")
        dbi.indicators = ind
        assert len(dbi.detected) == 0
        dbi.check_indicators()
        assert len(dbi.detected) == 2
