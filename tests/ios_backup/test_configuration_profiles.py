# Mobile Verification Toolkit (MVT)
# Copyright (c) 2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import pytest

from mvt.common.alerts import AlertLevel
from mvt.ios.modules.backup.configuration_profiles import ConfigurationProfiles

PROFILE_UUID = "ad43ba15-86af-4528-aaf4-11cd39cedc48"


def _profile_record(**values):
    return {
        "plist": {
            "PayloadUUID": PROFILE_UUID,
            "PayloadDisplayName": "Example profile",
            **values,
        },
        "install_date": "2026-10-22 12:00:00.000000",
    }


@pytest.mark.parametrize(
    "payload_types",
    [
        ["com.apple.notificationsettings"],
        ["com.apple.notificationsettings", "com.apple.wifi.managed"],
        ["com.apple.wifi.managed", "com.apple.notificationsettings"],
        [
            "com.apple.wifi.managed",
            "com.apple.security.root",
            "com.apple.notificationsettings",
        ],
        ["com.apple.notificationsettings", "com.apple.notificationsettings"],
    ],
)
def test_notification_payload_detected_in_any_position(
    indicators_factory, payload_types
):
    record = _profile_record(
        PayloadContent=[{"PayloadType": value} for value in payload_types]
    )
    module = ConfigurationProfiles(results=[record])
    module.indicators = indicators_factory()

    module.check_indicators()

    assert len(module.alertstore.alerts) == 1
    alert = module.alertstore.alerts[0]
    assert alert.level == AlertLevel.MEDIUM
    assert "com.apple.notificationsettings" in alert.message
    assert alert.event is record
    assert alert.matched_indicator is None


@pytest.mark.parametrize(
    "payload_fields",
    [{}, {"PayloadContent": []}, {"PayloadContent": None}],
)
@pytest.mark.parametrize("known_uuid", [False, True])
def test_missing_payloads_do_not_prevent_uuid_checks(
    indicators_factory, payload_fields, known_uuid
):
    record = _profile_record(**payload_fields)
    module = ConfigurationProfiles(results=[record])
    module.indicators = indicators_factory()
    if known_uuid:
        module.indicators.ioc_collections[0]["ios_profile_ids"].append(PROFILE_UUID)

    module.check_indicators()

    assert len(module.alertstore.alerts) == int(known_uuid)
    if known_uuid:
        alert = module.alertstore.alerts[0]
        assert alert.level == AlertLevel.CRITICAL
        assert alert.matched_indicator.value == PROFILE_UUID
        assert alert.event is record


def test_unrelated_payloads_do_not_trigger_notification_alert(indicators_factory):
    module = ConfigurationProfiles(
        results=[
            _profile_record(PayloadContent=[{"PayloadType": "com.apple.wifi.managed"}])
        ]
    )
    module.indicators = indicators_factory()

    module.check_indicators()

    assert module.alertstore.alerts == []


def test_known_uuid_keeps_critical_alert_precedence(indicators_factory):
    record = _profile_record(
        PayloadContent=[{"PayloadType": "com.apple.notificationsettings"}]
    )
    module = ConfigurationProfiles(results=[record])
    module.indicators = indicators_factory()
    module.indicators.ioc_collections[0]["ios_profile_ids"].append(PROFILE_UUID)

    module.check_indicators()

    assert len(module.alertstore.alerts) == 1
    assert module.alertstore.alerts[0].level == AlertLevel.CRITICAL
