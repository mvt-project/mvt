# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
"""The row's metadata is not part of the value.

`dumpsys settings` prints per-row metadata after the value. Keeping it inside
the value makes `check_indicators()` compare `"1 isValuePreservedInRestore:true"`
against a `safe_value` of `"1"` — so a setting that is in fact SAFE is reported
as suspicious. Local patch 0025.
"""

from mvt.android.artifacts.settings import Settings

HEADER = "GLOBAL SETTINGS (user 0)\n"


def _parse(rows):
    artifact = Settings()
    artifact.results = {}
    artifact.parse(HEADER + rows)
    return artifact.results["global:user_0"]


class TestSettingsValueIsStrippedOfRowMetadata:
    def test_metadata_after_default_system_set_is_dropped(self):
        # The shape the old inline regex missed: it anchored
        # `defaultSystemSet:(true|false)` to end of line.
        row = (
            "_id:36 name:lock_screen_show_notifications pkg:android value:1 "
            "default:1 defaultSystemSet:true isValuePreservedInRestore:true\n"
        )
        assert _parse(row)["lock_screen_show_notifications"] == "1"

    def test_restore_flag_without_a_default_is_dropped(self):
        rows = (
            "_id:5 name:quick_start_flow_type pkg:android value:4 "
            "notPreservedInRestore\n"
            "_id:9 name:send_action_app_error pkg:android value:1 "
            "isValuePreservedInRestore:true\n"
        )
        parsed = _parse(rows)
        assert parsed["quick_start_flow_type"] == "4"
        assert parsed["send_action_app_error"] == "1"

    def test_the_shape_that_already_worked_still_works(self):
        row = (
            "_id:12 name:adb_enabled pkg:com.android.shell value:0 "
            "default:0 defaultSystemSet:true\n"
        )
        assert _parse(row)["adb_enabled"] == "0"

    def test_a_value_containing_spaces_survives(self):
        # Metadata starts at the FIRST metadata key, not the last: a metadata
        # value can itself contain spaces.
        row = (
            "_id:20 name:device_name pkg:android value:Galaxy Z Flip6 "
            "default:Galaxy Z Flip6 defaultSystemSet:true\n"
        )
        assert _parse(row)["device_name"] == "Galaxy Z Flip6"

    def test_a_bare_value_is_unchanged(self):
        row = "_id:14 name:package_verifier_enable pkg:android value:1\n"
        assert _parse(row)["package_verifier_enable"] == "1"

    def test_safe_setting_no_longer_raises_an_alert(self):
        # send_action_app_error has safe_value "1"; before the fix the stored
        # value was "1 isValuePreservedInRestore:true" and it was flagged.
        artifact = Settings()
        artifact.results = {}
        artifact.parse(
            HEADER + "_id:9 name:send_action_app_error pkg:android value:1 "
            "isValuePreservedInRestore:true\n"
        )
        artifact.check_indicators()
        assert artifact.alertstore.alerts == []
