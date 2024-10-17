# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os

from mvt.common.indicators import Indicators
from ..utils import get_artifact_folder


class TestIndicators:
    def test_parse_stix2(self, indicator_file):
        ind = Indicators(log=logging)
        ind.load_indicators_files([indicator_file], load_default=False)
        assert len(ind.ioc_collections) == 1
        assert ind.ioc_collections[0]["count"] == 8
        assert len(ind.ioc_collections[0]["domains"]) == 1
        assert len(ind.ioc_collections[0]["emails"]) == 1
        assert len(ind.ioc_collections[0]["file_names"]) == 1
        assert len(ind.ioc_collections[0]["processes"]) == 1
        assert len(ind.ioc_collections[0]["android_property_names"]) == 1
        assert len(ind.ioc_collections[0]["files_sha256"]) == 1
        assert len(ind.ioc_collections[0]["files_sha1"]) == 1
        assert len(ind.ioc_collections[0]["urls"]) == 1

    def test_parse_stix2_amnesty(self):
        """
        STIX2 file from
        https://github.com/AmnestyTech/investigations/blob/master/2021-12-16_cytrox/cytrox.stix2
        """
        ind = Indicators(log=logging)
        file = os.path.join(get_artifact_folder(), "stix2", "cytrox.stix2")
        ind.load_indicators_files([file], load_default=False)
        assert len(ind.ioc_collections) == 1
        assert ind.ioc_collections[0]["count"] == 343
        assert len(ind.ioc_collections[0]["domains"]) == 336
        assert len(ind.ioc_collections[0]["emails"]) == 0
        assert len(ind.ioc_collections[0]["file_names"]) == 0
        assert len(ind.ioc_collections[0]["file_paths"]) == 6
        assert len(ind.ioc_collections[0]["ios_profile_ids"]) == 1
        assert len(ind.ioc_collections[0]["processes"]) == 0
        assert len(ind.ioc_collections[0]["android_property_names"]) == 0
        assert len(ind.ioc_collections[0]["urls"]) == 0

    def test_parse_stix2_otx(self):
        """
        STIX2 file from OTX Pulse
        https://otx.alienvault.com/pulse/638cd3ee5e5f019f84f9e0ea
        """
        ind = Indicators(log=logging)
        file = os.path.join(
            get_artifact_folder(), "stix2", "638cd3ee5e5f019f84f9e0ea.json"
        )
        ind.load_indicators_files([file], load_default=False)
        assert len(ind.ioc_collections) == 1
        assert ind.ioc_collections[0]["count"] == 69
        assert len(ind.ioc_collections[0]["domains"]) == 15
        assert len(ind.ioc_collections[0]["emails"]) == 0
        assert len(ind.ioc_collections[0]["file_names"]) == 0
        assert len(ind.ioc_collections[0]["processes"]) == 0
        assert len(ind.ioc_collections[0]["android_property_names"]) == 0
        assert len(ind.ioc_collections[0]["urls"]) == 54

    def test_check_url(self, indicator_file):
        ind = Indicators(log=logging)
        ind.load_indicators_files([indicator_file], load_default=False)
        assert ind.check_url(42) is None
        assert ind.check_url("http://example.com/thisisbad")
        assert ind.check_url("http://example.com/thisisgood") is None
        assert ind.check_url("https://www.example.org/foobar")
        assert ind.check_url("http://example.org:8080/toto")
        assert ind.check_url("https://github.com") is None
        assert ind.check_url("https://example.com/") is None

    def test_check_file_hash(self, indicator_file):
        ind = Indicators(log=logging)
        ind.load_indicators_files([indicator_file], load_default=False)
        assert (
            ind.check_file_hash(
                "003764fd74bf13cff9bf1ddd870cbf593b23e2b584ba4465114023870ea6fbef"
            )
            is None
        )
        assert ind.check_file_hash(
            "570cd76bf49cf52e0cb347a68bdcf0590b2eaece134e1b1eba7e8d66261bdbe6"
        )
        assert ind.check_file_hash("da0611a300a9ce9aa7a09d1212f203fca5856794")

    def test_check_android_property(self, indicator_file):
        ind = Indicators(log=logging)
        ind.load_indicators_files([indicator_file], load_default=False)
        assert ind.check_android_property_name("sys.foobar")
        assert ind.check_android_property_name("sys.soundsokay") is None

    def test_env_stix(self, indicator_file):
        os.environ["MVT_STIX2"] = indicator_file
        ind = Indicators(log=logging)
        ind.load_indicators_files([], load_default=False)
        assert ind.total_ioc_count == 8
