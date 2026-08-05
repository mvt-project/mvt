# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from mvt.android.artifacts.dumpsys_adb import DumpsysADBArtifact
from mvt.android.modules.bugreport.dumpsys_adb_state import DumpsysADBState
from mvt.common.alerts import AlertLevel

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


class TestDumpsysADBStateAlerts:
    def test_no_androidqf_context_preserves_existing_behavior(self):
        module = DumpsysADBState(
            results=[
                {
                    "user_keys": [
                        {
                            "key": b"QUJDRA==",
                            "user": "host@example",
                            "fingerprint": "fingerprint",
                        }
                    ]
                }
            ]
        )

        module.check_indicators()

        assert module.alertstore.alerts == []

    def test_androidqf_trusted_keys_create_expected_alerts(self):
        module = DumpsysADBState(
            module_options={
                "androidqf_acquisition": {
                    "started": "2025-06-20T18:00:00Z",
                    "adb_host_public_key": "QUJDRA== acquisition@host",
                }
            },
            results=[
                {
                    "user_keys": [
                        {
                            "key": b"QUJDRA==",
                            "user": "acquisition@host",
                            "fingerprint": "acquisition-fingerprint",
                        },
                        {
                            "key": b"RUZHSA==",
                            "user": "other@host",
                            "fingerprint": "other-fingerprint",
                        },
                        {
                            "key": b"not-base64",
                            "user": "invalid@host",
                            "fingerprint": "",
                        },
                    ],
                    "keystore": [
                        {
                            "key": b"QUJDRA==",
                            "user": "acquisition@host",
                            "fingerprint": "acquisition-fingerprint",
                            "last_connected": "1750266000000",
                        }
                    ],
                }
            ],
        )

        module.check_indicators()

        assert [alert.level for alert in module.alertstore.alerts] == [
            AlertLevel.INFORMATIONAL,
            AlertLevel.LOW,
            AlertLevel.LOW,
        ]
        informational, different, invalid = module.alertstore.alerts
        assert "at least one day before" in informational.message
        assert informational.event_time == "2025-06-18 17:00:00.000000"
        assert "different from the AndroidQF acquisition host" in different.message
        assert "invalid trusted ADB host key" in invalid.message

    def test_missing_androidqf_host_key_creates_low_alert(self):
        trusted_key = {
            "key": b"QUJDRA==",
            "user": "host@example",
            "fingerprint": "fingerprint",
        }
        module = DumpsysADBState(
            module_options={"androidqf_acquisition": {}},
            results=[{"user_keys": [trusted_key]}],
        )

        module.check_indicators()

        assert len(module.alertstore.alerts) == 1
        assert module.alertstore.alerts[0].level == AlertLevel.LOW
        assert "does not include its host key" in module.alertstore.alerts[0].message

    def test_recent_acquisition_host_key_does_not_create_alert(self):
        module = DumpsysADBState(
            module_options={
                "androidqf_acquisition": {
                    "started": "2025-06-20T18:00:00Z",
                    "adb_host_public_key": "QUJDRA== acquisition@host",
                }
            },
            results=[
                {
                    "keystore": [
                        {
                            "key": b"QUJDRA==",
                            "user": "acquisition@host",
                            "fingerprint": "fingerprint",
                            "last_connected": "1750438800000",
                        }
                    ]
                }
            ],
        )

        module.check_indicators()

        assert module.alertstore.alerts == []
