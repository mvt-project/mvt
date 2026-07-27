# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
import threading

import requests

from mvt.common.config import settings
from mvt.common.indicators import Indicators
from ..utils import get_artifact_folder


class TestIndicators:
    def test_parse_stix2(self, indicator_file):
        ind = Indicators(log=logging)
        ind.load_indicators_files([indicator_file], load_default=False)
        assert len(ind.ioc_collections) == 1
        assert ind.ioc_collections[0]["count"] == 9
        assert len(ind.ioc_collections[0]["domains"]) == 2
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

        # Test detecting IP address indicators from STIX.
        assert ind.check_url("https://198.51.100.1:8080/")
        assert ind.check_url("https://1.1.1.1/") is None

    def test_google_maps_short_url_is_not_resolved(self, indicator_file, mocker):
        head_request = mocker.patch("mvt.common.url.requests.head")
        ind = Indicators(log=logging)
        ind.load_indicators_files([indicator_file], load_default=False)

        assert ind.check_url("https://goo.gl/maps/example") is None
        head_request.assert_not_called()

    def test_check_url_batches_preserves_order(self, indicator_file):
        ind = Indicators(log=logging)
        ind.load_indicators_files([indicator_file], load_default=False)

        matches = ind.check_url_batches(
            [
                [
                    "https://github.com",
                    "http://example.com/thisisbad",
                    "https://www.example.org/foobar",
                ],
                ["https://github.com", "https://www.example.org/foobar"],
                [],
                None,
            ]
        )

        assert matches[0]
        assert matches[0].ioc.value == "http://example.com/thisisbad"
        assert matches[1]
        assert matches[1].ioc.value == "example.org"
        assert matches[2] is None
        assert matches[3] is None

    def test_check_url_batches_deduplicates_and_limits_workers(
        self, indicator_file, mocker
    ):
        ind = Indicators(log=logging)
        ind.load_indicators_files([indicator_file], load_default=False)
        mocker.patch("mvt.common.indicators.URL_CHECK_MAX_WORKERS", 2)

        barrier = threading.Barrier(2)
        lock = threading.Lock()
        calls = []
        active = 0
        max_active = 0

        def head_request(url, timeout):
            nonlocal active, max_active
            with lock:
                calls.append(url)
                active += 1
                max_active = max(max_active, active)
                call_number = len(calls)

            try:
                if call_number <= 2:
                    barrier.wait(timeout=5)
                return mocker.Mock(status_code=200, headers={})
            finally:
                with lock:
                    active -= 1

        mocker.patch("mvt.common.url.requests.head", side_effect=head_request)
        urls = [
            "https://bit.ly/one",
            "https://tinyurl.com/two",
            "https://t.co/three",
        ]

        assert ind.check_url_batches([urls, [urls[0]]]) == [None, None]
        assert sorted(calls) == sorted(urls)
        assert max_active == 2

    def test_check_url_batches_respects_disabled_network(
        self, indicator_file, mocker
    ):
        ind = Indicators(log=logging)
        ind.load_indicators_files([indicator_file], load_default=False)
        mocker.patch("mvt.common.indicators.settings.NETWORK_ACCESS_ALLOWED", False)
        head_request = mocker.patch("mvt.common.url.requests.head")

        assert ind.check_url_batches([["https://bit.ly/example"]]) == [None]
        head_request.assert_not_called()

    def test_check_url_batches_handles_nested_redirects_and_request_failures(
        self, indicator_file, mocker
    ):
        ind = Indicators(log=logging)
        ind.load_indicators_files([indicator_file], load_default=False)

        def head_request(url, timeout):
            if url == "https://bit.ly/failure":
                raise requests.Timeout()
            if url == "https://tinyurl.com/nested":
                return mocker.Mock(
                    status_code=301,
                    headers={"Location": "https://t.co/nested"},
                )
            if url == "https://t.co/nested":
                return mocker.Mock(
                    status_code=302,
                    headers={"Location": "https://www.example.org/landing"},
                )
            raise AssertionError(f"Unexpected URL: {url}")

        head = mocker.patch(
            "mvt.common.url.requests.head", side_effect=head_request
        )

        matches = ind.check_url_batches(
            [["https://bit.ly/failure"], ["https://tinyurl.com/nested"]]
        )

        assert matches[0] is None
        assert matches[1]
        assert matches[1].ioc.value == "example.org"
        assert {call.args[0] for call in head.call_args_list} == {
            "https://bit.ly/failure",
            "https://tinyurl.com/nested",
            "https://t.co/nested",
        }

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

    def test_parse_stix2_hash_key_variants(self, tmp_path):
        """STIX2 spec requires single-quoted algorithm names that contain hyphens,
        e.g. file:hashes.'SHA-256'. Verify MVT accepts both spec-compliant and
        non-standard lowercase spellings for MD5, SHA-1 and SHA-256."""
        import json

        sha256_hash = "570cd76bf49cf52e0cb347a68bdcf0590b2eaece134e1b1eba7e8d66261bdbe6"
        sha1_hash = "da0611a300a9ce9aa7a09d1212f203fca5856794"
        md5_hash = "d41d8cd98f00b204e9800998ecf8427e"

        variants = [
            # (pattern_key, expected_bucket)
            ("file:hashes.'SHA-256'", "files_sha256"),
            ("file:hashes.SHA-256", "files_sha256"),
            ("file:hashes.SHA256", "files_sha256"),
            ("file:hashes.sha256", "files_sha256"),
            ("file:hashes.'SHA-1'", "files_sha1"),
            ("file:hashes.SHA-1", "files_sha1"),
            ("file:hashes.SHA1", "files_sha1"),
            ("file:hashes.sha1", "files_sha1"),
            ("file:hashes.MD5", "files_md5"),
            ("file:hashes.'MD5'", "files_md5"),
            ("file:hashes.md5", "files_md5"),
        ]

        hash_for = {
            "files_sha256": sha256_hash,
            "files_sha1": sha1_hash,
            "files_md5": md5_hash,
        }

        for pattern_key, bucket in variants:
            h = hash_for[bucket]
            stix = {
                "type": "bundle",
                "id": "bundle--test",
                "objects": [
                    {
                        "type": "malware",
                        "id": "malware--test",
                        "name": "TestMalware",
                        "is_family": False,
                    },
                    {
                        "type": "indicator",
                        "id": "indicator--test",
                        "indicator_types": ["malicious-activity"],
                        "pattern": f"[{pattern_key}='{h}']",
                        "pattern_type": "stix",
                        "valid_from": "2024-01-01T00:00:00Z",
                    },
                    {
                        "type": "relationship",
                        "id": "relationship--test",
                        "relationship_type": "indicates",
                        "source_ref": "indicator--test",
                        "target_ref": "malware--test",
                    },
                ],
            }
            stix_file = tmp_path / "test.stix2"
            stix_file.write_text(json.dumps(stix))

            ind = Indicators(log=logging)
            ind.load_indicators_files([str(stix_file)], load_default=False)
            assert len(ind.ioc_collections[0][bucket]) == 1, (
                f"Pattern key '{pattern_key}' was not parsed into '{bucket}'"
            )
            assert ind.check_file_hash(h) is not None, (
                f"check_file_hash failed for pattern key '{pattern_key}'"
            )

    def test_check_android_property(self, indicator_file):
        ind = Indicators(log=logging)
        ind.load_indicators_files([indicator_file], load_default=False)
        assert ind.check_android_property_name("sys.foobar")
        assert ind.check_android_property_name("sys.soundsokay") is None

    def test_env_stix(self, indicator_file):
        os.environ["MVT_STIX2"] = indicator_file
        settings.__init__()  # Reset settings

        ind = Indicators(log=logging)
        ind.load_indicators_files([], load_default=False)
        assert ind.total_ioc_count == 9
