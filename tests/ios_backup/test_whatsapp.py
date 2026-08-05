# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

from mvt.common.indicators import Indicators
from mvt.ios.modules.mixed.whatsapp import Whatsapp


def test_collect_url_results_includes_expansion():
    module = Whatsapp(
        results=[
            {
                "links": ["https://bit.ly/message"],
                "isodate": "2026-07-29 12:00:00.000000",
            }
        ]
    )
    module.indicators = Indicators(log=logging.getLogger())
    module.indicators.resolved_urls["https://bit.ly/message"] = (
        "https://example.org/landing"
    )

    module.collect_url_results()

    assert module.url_results == [
        {
            "url": "https://bit.ly/message",
            "expanded_url": "https://example.org/landing",
            "timestamp": "2026-07-29 12:00:00.000000",
            "source": "whatsapp",
        }
    ]
