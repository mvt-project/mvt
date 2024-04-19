# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import json
import logging
import os
from datetime import datetime

from mvt.common.utils import (
    CustomJSONEncoder,
    convert_datetime_to_iso,
    convert_mactime_to_iso,
    convert_unix_to_iso,
    convert_unix_to_utc_datetime,
    generate_hashes_from_path,
    get_sha256_from_file_path,
)

from ..utils import get_artifact_folder

TEST_DATE_EPOCH = 1626566400
TEST_DATE_ISO = "2021-07-18 00:00:00.000000"
TEST_DATE_MAC = TEST_DATE_EPOCH - 978307200


class TestDateConversions:
    def test_convert_unix_to_iso(self):
        assert convert_unix_to_iso(TEST_DATE_EPOCH) == TEST_DATE_ISO

    def test_convert_mactime_to_iso(self):
        assert convert_mactime_to_iso(TEST_DATE_MAC) == TEST_DATE_ISO

    def test_convert_unix_to_utc_datetime(self):
        converted = convert_unix_to_utc_datetime(TEST_DATE_EPOCH)
        assert converted.year == 2021
        assert converted.month == 7
        assert converted.day == 18

    def test_convert_datetime_to_iso(self):
        converted = convert_unix_to_utc_datetime(TEST_DATE_EPOCH)
        assert convert_datetime_to_iso(converted) == TEST_DATE_ISO

    def test_convert_timezone_aware_to_iso(self):
        assert (
            convert_datetime_to_iso(
                datetime.strptime("2024-09-30 11:21:20+0200", "%Y-%m-%d %H:%M:%S%z")
            )
            == "2024-09-30 09:21:20.000000"
        )


class TestHashes:
    def test_hash_from_file(self):
        path = os.path.join(get_artifact_folder(), "androidqf", "backup.ab")
        sha256 = get_sha256_from_file_path(path)
        assert (
            sha256 == "f0e32fe8a7fd5ac0e2de19636d123c0072e979396986139ba2bc49ec385dc325"
        )

    def test_hash_from_folder(self):
        path = os.path.join(get_artifact_folder(), "androidqf")
        hashes = list(generate_hashes_from_path(path, logging))
        assert len(hashes) == 5
        # Sort the files to have reliable order for tests.
        hashes = sorted(hashes, key=lambda x: x["file_path"])
        assert hashes[0]["file_path"] == os.path.join(path, "backup.ab")
        assert (
            hashes[0]["sha256"]
            == "f0e32fe8a7fd5ac0e2de19636d123c0072e979396986139ba2bc49ec385dc325"
        )
        assert hashes[1]["file_path"] == os.path.join(path, "dumpsys.txt")
        assert (
            hashes[1]["sha256"]
            == "cfae0e04ef139b5a2ae1e2b3d400ce67eb98e67ff66f56ba2a580fe41bc120d0"
        )


class TestCustomJSONEncoder:
    def test__normal_input(self):
        assert json.dumps({"a": "b"}, cls=CustomJSONEncoder) == '{"a": "b"}'

    def test__datetime_object(self):
        assert (
            json.dumps(
                {"timestamp": datetime(2023, 11, 13, 12, 21, 49, 727467)},
                cls=CustomJSONEncoder,
            )
            == '{"timestamp": "2023-11-13 12:21:49.727467"}'
        )

    def test__bytes_non_utf_8(self):
        assert (
            json.dumps({"identifier": b"\xa8\xa9"}, cls=CustomJSONEncoder)
            == """{"identifier": "\\\\xa8\\\\xa9"}"""
        )

    def test__bytes_valid_utf_8(self):
        assert (
            json.dumps({"name": "家".encode()}, cls=CustomJSONEncoder)
            == '{"name": "\\u5bb6"}'
        )
