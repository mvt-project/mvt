# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from mvt.ios.versions import is_ios_version_outdated


class TestIosVersions:
    def test_is_ios_version_outdated(self):
        assert is_ios_version_outdated("20B110") is True
        assert is_ios_version_outdated("16.3") is True
        assert is_ios_version_outdated("38.2") is False
