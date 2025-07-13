# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from mvt.android.artifacts.dumpsys_adb import DumpsysADBArtifact

from ..utils import get_artifact


class TestDumpsysADBArtifact:
    def test_parsing(self):
        da_adb = DumpsysADBArtifact()
        file = get_artifact("android_data/dumpsys_adb.txt")
        with open(file, "rb") as f:
            data = f.read()

        assert len(da_adb.results) == 0
        da_adb.parse(data)

        assert len(da_adb.results) == 1
        adb_data = da_adb.results[0]
        assert "user_keys" in adb_data
        assert len(adb_data["user_keys"]) == 1

        # Check key and fingerprint parsed successfully.
        user_key = adb_data["user_keys"][0]
        assert (
            user_key["fingerprint"] == "F0:A1:3D:8C:B3:F4:7B:09:9F:EE:8B:D8:38:2E:BD:C6"
        )
        assert user_key["user"] == "user@linux"

    def test_parsing_adb_xml(self):
        da_adb = DumpsysADBArtifact()
        file = get_artifact("android_data/dumpsys_adb_xml.txt")
        with open(file, "rb") as f:
            data = f.read()

        da_adb.parse(data)

        assert len(da_adb.results) == 1

        adb_data = da_adb.results[0]
        assert "user_keys" in adb_data
        assert len(adb_data["user_keys"]) == 1

        # Check key and fingerprint parsed successfully.
        expected_fingerprint = "F0:0B:27:08:E3:68:7B:FA:4C:79:A2:B4:BF:0E:CF:70"
        user_key = adb_data["user_keys"][0]
        user_key["fingerprint"] == expected_fingerprint
        assert user_key["user"] == "user@laptop"

        key_store_entry = adb_data["keystore"][0]
        assert key_store_entry["user"] == "user@laptop"
        assert key_store_entry["fingerprint"] == expected_fingerprint
        assert key_store_entry["last_connected"] == "1628501829898"
