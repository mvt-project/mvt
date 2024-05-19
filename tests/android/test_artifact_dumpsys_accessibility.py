# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
import logging

from mvt.android.artifacts.dumpsys_accessibility import DumpsysAccessibilityArtifact
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
            da.results[0]["service"]
            == "com.android.settings/com.samsung.android.settings.development.gpuwatch.GPUWatchInterceptor"
        )

    def test_parsing_v14_aosp_format(self):
        da = DumpsysAccessibilityArtifact()
        file = get_artifact("android_data/dumpsys_accessibility_v14_or_later.txt")
        with open(file) as f:
            data = f.read()

        assert len(da.results) == 0
        da.parse(data)
        assert len(da.results) == 1
        assert da.results[0]["package_name"] == "com.malware.accessibility"
        assert da.results[0]["service"] == "com.malware.service.malwareservice"

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
        assert len(da.detected) == 0
        da.check_indicators()
        assert len(da.detected) == 1
