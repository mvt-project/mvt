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


@pytest.mark.parametrize(
    "url, domain",
    [
        ("https://www.example.com/path", "example.com"),
        # Only the whole "www." prefix comes off, not any leading "w" or "." character.
        ("https://web.example.com", "web.example.com"),
        ("https://wow.com", "wow.com"),
        ("https://wired.com", "wired.com"),
        ("https://www.wow.com", "wow.com"),
    ],
)
def test_get_domain_strips_only_a_whole_www_prefix(url, domain):
    assert URL(url).domain == domain


@pytest.mark.parametrize(
    "url",
    [
        "https://payload.example.org:443/path",
        "https://user:password@payload.example.org/path",
        "https://user:password@www.payload.example.org:8443/path",
        "payload.example.org:443/path",
    ],
)
def test_get_domain_excludes_port_and_credentials(url):
    assert URL(url).domain == "payload.example.org"


def test_shortener_with_port_and_credentials_is_detected():
    assert URL("https://user:password@bit.ly:443/example").check_if_shortened()


def test_shortener_starting_with_w_is_detected():
    assert URL("https://w3t.org/example").check_if_shortened() is True
    assert URL("https://www.w3t.org/example").check_if_shortened() is True
