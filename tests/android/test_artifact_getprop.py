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
        assert len(gp.alertstore.alerts) == 0
        gp.check_indicators()
        assert len(gp.alertstore.alerts) == 1

    def test_empty_values_and_invalid_lines(self):
        gp = GetProp()
        gp.parse("[empty]: []\n[valid]: [value]\n0\n[broken]: [value")

        assert gp.results == [
            {"name": "empty", "value": ""},
            {"name": "valid", "value": "value"},
        ]

    def test_multiline_value(self):
        gp = GetProp()
        gp.parse(
            "[persist.sys.boot.reason.history]: ["
            "reboot,ota,1697044974\n"
            "reboot,watchdog,1696958574]\n"
            "[ro.build.version.sdk]: [35]\n"
        )

        assert gp.results == [
            {
                "name": "persist.sys.boot.reason.history",
                "value": "reboot,ota,1697044974\nreboot,watchdog,1696958574",
            },
            {"name": "ro.build.version.sdk", "value": "35"},
        ]
