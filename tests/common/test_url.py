# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import pytest

from mvt.common.url import URL


@pytest.mark.parametrize(
    "url",
    [
        "https://goo.gl/maps/example",
        "http://goo.gl/maps/example?entry=message",
        "goo.gl/maps/example",
    ],
)
def test_google_maps_url_is_not_shortened(url):
    assert URL(url).check_if_shortened() is False


def test_other_google_short_url_is_shortened():
    assert URL("https://goo.gl/example").check_if_shortened() is True
