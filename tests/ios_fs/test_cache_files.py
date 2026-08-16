# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
import logging

from mvt.common.indicators import Indicators
from mvt.ios.modules.fs.cache_files import CacheFiles


class TestCacheFiles:
    def test_detection(self, indicator_file):
        m = CacheFiles(
            results={
                "Library/Caches/example/Cache.db": [
                    {
                        "entry_id": 1,
                        "version": 1,
                        "hash_value": 123,
                        "storage_policy": 0,
                        "url": "http://example.com/thisisbad",
                        "isodate": "2026-01-01 00:00:00.000000",
                    }
                ]
            }
        )
        ind = Indicators(log=logging.getLogger())
        ind.parse_stix2(indicator_file)
        m.indicators = ind

        m.check_indicators()

        assert len(m.alertstore.alerts) == 1
        alert = m.alertstore.alerts[0]
        assert alert.event["cache_file"] == "Library/Caches/example/Cache.db"
        assert alert.event["url"] == "http://example.com/thisisbad"
        assert alert.matched_indicator is not None
