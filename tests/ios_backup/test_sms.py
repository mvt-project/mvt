# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

from mvt.common.indicators import Indicators
from mvt.common.module import run_module
from mvt.ios.modules.mixed.sms import SMS

from ..utils import get_ios_backup_folder


class TestSMSModule:
    def test_sms(self):
        m = SMS(target_path=get_ios_backup_folder())
        run_module(m)
        assert len(m.results) == 1
        assert len(m.timeline) == 2
        assert m.url_results == [
            {
                "url": "https://badbadbad.example.org/",
                "expanded_url": None,
                "timestamp": "2019-08-29 23:13:30.000000",
                "source": "sms",
            }
        ]
        assert len(m.alertstore.alerts) == 0

    def test_detection(self, indicator_file):
        m = SMS(target_path=get_ios_backup_folder())
        ind = Indicators(log=logging.getLogger())
        ind.parse_stix2(indicator_file)
        # Adds a file that exists in the manifest.
        ind.ioc_collections[0]["domains"].append("badbadbad.example.org")
        m.indicators = ind
        run_module(m)
        assert len(m.alertstore.alerts) == 1

    def test_detection_batches_urls_and_preserves_event(self, indicator_file, mocker):
        results = [
            {
                "text": "first",
                "links": ["http://example.com/thisisbad"],
            },
            {
                "text": "second",
                "links": ["https://github.com"],
            },
        ]
        m = SMS(results=results)
        ind = Indicators(log=logging.getLogger())
        ind.parse_stix2(indicator_file)
        batch_check = mocker.spy(ind, "check_url_batches")
        m.indicators = ind

        m.check_indicators()

        batch_check.assert_called_once_with(
            [
                ["http://example.com/thisisbad"],
                ["https://github.com"],
            ]
        )
        assert len(m.alertstore.alerts) == 1
        assert m.alertstore.alerts[0].event is results[0]
