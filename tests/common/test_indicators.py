# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os

from mvt.common.indicators import Indicators


class TestIndicators:
    def test_parse_stix2(self, indicator_file):
        ind = Indicators(log=logging)
        ind.load_indicators_files([indicator_file], load_default=False)
        assert ind.ioc_collections[0]["count"] == 5
        assert len(ind.ioc_collections[0]["domains"]) == 1
        assert len(ind.ioc_collections[0]["emails"]) == 1
        assert len(ind.ioc_collections[0]["file_names"]) == 1
        assert len(ind.ioc_collections[0]["processes"]) == 1
        assert len(ind.ioc_collections[0]["android_property_names"]) == 1

    def test_check_domain(self, indicator_file):
        ind = Indicators(log=logging)
        ind.load_indicators_files([indicator_file], load_default=False)
        assert ind.check_domain(42) is None
        assert ind.check_domain("https://www.example.org/foobar")
        assert ind.check_domain("http://example.org:8080/toto")
        assert ind.check_domain("https://github.com") is None

    def test_check_android_property(self, indicator_file):
        ind = Indicators(log=logging)
        ind.load_indicators_files([indicator_file], load_default=False)
        assert ind.check_android_property_name("sys.foobar")
        assert ind.check_android_property_name("sys.soundsokay") is None

    def test_env_stix(self, indicator_file):
        os.environ["MVT_STIX2"] = indicator_file
        ind = Indicators(log=logging)
        ind.load_indicators_files([], load_default=False)
        assert ind.total_ioc_count == 5
