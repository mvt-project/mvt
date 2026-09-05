# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from mvt.android.artifacts.settings import Settings

from ..utils import get_artifact


def parse_bugreport_settings() -> Settings:
    settings = Settings()
    with open(get_artifact("android_data/bugreport/dumpstate.txt")) as handle:
        data = handle.read()

    settings.parse(settings.extract_dumpsys_section(data, "DUMP OF SERVICE settings:"))
    return settings


def find(settings: Settings, name: str) -> list:
    return [result for result in settings.results if result["name"] == name]


class TestSettingsArtifact:
    def test_parsing(self):
        settings = parse_bugreport_settings()

        assert len(settings.results) == 12
        assert {result["namespace"] for result in settings.results} == {
            "config",
            "global",
            "secure",
        }
        assert settings.results[0] == {
            "namespace": "config",
            "user": "0",
            "_id": "682",
            "name": "namespace_one/blocked_components",
            "pkg": "com.example.services",
            "value": (
                "com.android.settings,com.android.vending,\n"
                "com.example.dialer,\n"
                "com.example.camera"
            ),
            "default": (
                "com.android.settings,\n"
                "        com.android.vending,\n"
                "        com.example.dialer"
            ),
            "defaultSystemSet": "false",
            "history": [],
        }

    def test_multiline_values_are_kept_whole(self):
        settings = parse_bugreport_settings()

        assert find(settings, "namespace_one/allowed_packages")[0]["value"] == (
            "com.example.messaging,\ncom.example.chat"
        )
        assert find(settings, "widget_instance_data")[0]["value"] == (
            '{\n  "version": 1,\n  "data": [\n    {\n      "number": 10000,\n'
            '      "package_name": "com.example.widget"\n    }\n  ]\n}'
        )

    def test_trailing_default_is_not_part_of_the_value(self):
        settings = parse_bugreport_settings()

        record = find(settings, "namespace_one/streaming_blocked_components")[0]
        assert record["value"] == "com.example.dialer,com.example.camera"
        assert record["default"] == "com.android.settings,\n        com.android.vending"

    def test_trailing_metadata_is_not_part_of_the_value(self):
        settings = parse_bugreport_settings()

        record = find(settings, "lock_screen_show_notifications")[0]
        assert record["value"] == "1"
        assert record["defaultSystemSet"] == "true"
        assert record["isValuePreservedInRestore"] == "true"

        # Without a default, the tag or the restore token follows the value.
        record = find(settings, "accessibility_enabled")[1]
        assert record["value"] == "0"
        assert record["tag"] == "null"
        assert "default" not in record

        record = find(settings, "send_action_app_error")[0]
        assert record["value"] == "1"
        assert record["isValuePreservedInRestore"] == "false"

    def test_dumps_after_the_last_block_are_not_part_of_the_last_row(self):
        settings = parse_bugreport_settings()

        assert settings.results[-1] == {
            "namespace": "secure",
            "user": "10",
            "_id": "311",
            "name": "accessibility_enabled",
            "pkg": "android",
            "value": "0",
            "tag": "null",
            "history": [],
        }

    def test_repeated_names_are_kept_as_separate_records(self):
        settings = parse_bugreport_settings()

        widgets = find(settings, "widget_instance_data")
        assert [record["_id"] for record in widgets] == ["771", "41654"]

        accessibility = find(settings, "accessibility_enabled")
        assert [(record["user"], record["value"]) for record in accessibility] == [
            ("0", "1"),
            ("10", "0"),
        ]

    def test_setting_without_recording_package(self):
        settings = parse_bugreport_settings()

        record = find(settings, "hidden_api_blacklist_exemptions")[0]
        assert "pkg" not in record
        assert record["value"] == "{null}"

    def test_history_timestamps_resolved_against_section_end(self):
        settings = parse_bugreport_settings()

        # The section was dumped on 2022-03-29, so an 11-02 entry belongs to
        # the previous year and an 03-14 entry to the same year.
        assert find(settings, "development_settings_enabled")[0]["history"] == [
            {
                "timestamp": "2021-11-02 11:21:22.212000",
                "oldValue": "null",
                "newValue": "1",
                "pkg": "com.android.settings",
            },
            {
                "timestamp": "2022-03-14 09:02:11.100000",
                "oldValue": "1",
                "newValue": "0",
                "pkg": "com.example.updater",
            },
        ]

    def test_history_without_a_section_end_has_no_timestamp(self):
        settings = Settings()
        settings.parse(
            "SECURE SETTINGS (user 0)\n"
            "_id:240 name:accessibility_enabled pkg:android value:1\n"
            "\tHistory (accessibility_enabled)\n"
            "\t\ttime:03-28 22:41:07.980 mode:update oldValue:0 newValue:1 "
            "package:com.example.helper\n"
        )

        assert settings.results[0]["history"] == [
            {
                "timestamp": None,
                "oldValue": "0",
                "newValue": "1",
                "pkg": "com.example.helper",
            }
        ]

    def test_dangerous_setting_is_detected_with_the_changing_package(self):
        settings = parse_bugreport_settings()
        settings.check_indicators()

        assert len(settings.alertstore.alerts) == 1
        alert = settings.alertstore.alerts[0]
        assert "accessibility_enabled = 1" in alert.message
        assert alert.event_time == "2022-03-28 22:41:07.980000"
        assert alert.event["history"][0]["pkg"] == "com.example.helper"
