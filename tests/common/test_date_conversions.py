# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from mvt.common.utils import convert_mactime_to_iso, convert_unix_to_iso

TEST_DATE_EPOCH = 1626566400
TEST_DATE_ISO = "2021-07-18 00:00:00.000000"
TEST_DATE_MAC = TEST_DATE_EPOCH - 978307200


class TestDateConversions:

    def test_convert_unix_to_iso(self):
        assert convert_unix_to_iso(TEST_DATE_EPOCH) == TEST_DATE_ISO

    def test_convert_mactime_to_iso(self):
        assert convert_mactime_to_iso(TEST_DATE_MAC) == TEST_DATE_ISO
