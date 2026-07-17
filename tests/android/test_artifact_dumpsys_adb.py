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

    def test_parsing_adb_wifi(self):
        da_adb = DumpsysADBArtifact()
        file = get_artifact("android_data/dumpsys_adb_wifi.txt")
        with open(file, "rb") as f:
            data = f.read()

        da_adb.parse(data)

        assert len(da_adb.results) == 1
        adb_data = da_adb.results[0]
        assert "user_keys" in adb_data
        assert len(adb_data["user_keys"]) == 1

        user_key = adb_data["user_keys"][0]
        assert (
            user_key["fingerprint"] == "F0:A1:3D:8C:B3:F4:7B:09:9F:EE:8B:D8:38:2E:BD:C6"
        )
        assert user_key["user"] == "user@linux"

        # The adb_wifi block following the keystore is not part of the keystore.
        assert b"adb_wifi" not in adb_data["keystore"]

    def test_parsing_multiline_terminated_by_structural_line(self):
        dump_data = (
            b"debugging_manager={\n"
            b"  keystore=ABX\x00\x0bkeyStore\x00\x02\x11\n"
            b"  connected_to_adb=true\n"
            b"  adb_wifi={\n"
            b"    enabled=false\n"
            b"    tls_port=0\n"
            b"  }\n"
        )

        parsed = DumpsysADBArtifact().indented_dump_parser(dump_data)

        debugging_manager = parsed["debugging_manager"]
        assert debugging_manager["keystore"] == [b"ABX\x00\x0bkeyStore\x00\x02\x11"]
        assert debugging_manager["connected_to_adb"] == b"true"
        assert debugging_manager["adb_wifi"] == {
            "enabled": b"false",
            "tls_port": b"0",
        }

    def test_parsing_multiline_terminated_by_closing_brace(self):
        dump_data = (
            b"debugging_manager={\n"
            b"  keystore=ABX\x00\x0bkeyStore\x00\x02\x11\n"
            b"}\n"
            b"other={\n"
            b"  value=true\n"
            b"}\n"
        )

        parsed = DumpsysADBArtifact().indented_dump_parser(dump_data)

        assert parsed["debugging_manager"]["keystore"] == [
            b"ABX\x00\x0bkeyStore\x00\x02\x11"
        ]
        assert parsed["other"] == {"value": b"true"}

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
