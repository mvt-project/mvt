# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
import logging

from mvt.android.artifacts.getprop import GetProp
from mvt.common.indicators import Indicators

from ..utils import get_artifact


class TestGetPropArtifact:
    def test_parsing(self):
        gp = GetProp()
        file = get_artifact("android_data/getprop.txt")
        with open(file) as f:
            data = f.read()

        assert len(gp.results) == 0
        gp.parse(data)
        assert len(gp.results) == 13
        assert gp.results[0]["name"] == "af.fast_track_multiplier"
        assert gp.results[0]["value"] == "1"

    def test_ioc_check(self, indicator_file):
        gp = GetProp()
        file = get_artifact("android_data/getprop.txt")
        with open(file) as f:
            data = f.read()
        gp.parse(data)

        ind = Indicators(log=logging.getLogger())
        ind.parse_stix2(indicator_file)
        ind.ioc_collections[0]["android_property_names"].append(
            "dalvik.vm.appimageformat"
        )
        gp.indicators = ind
        assert len(gp.detected) == 0
        gp.check_indicators()
        assert len(gp.detected) == 1
