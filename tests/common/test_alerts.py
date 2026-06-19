# Mobile Verification Toolkit (MVT)
# Copyright (c) 2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from mvt.common.alerts import Alert, AlertLevel, AlertStore


def test_as_json_promotes_nested_matched_indicator():
    indicator = {"value": "com.apple.weather", "type": "processes"}
    alertstore = AlertStore()
    alertstore.add(
        Alert(
            level=AlertLevel.CRITICAL,
            module="datausage",
            message="Matched indicator",
            event_time="2026-01-01 00:00:00",
            event={
                "proc_name": "WeatherWidget/com.apple.weather",
                "matched_indicator": indicator,
            },
        )
    )

    alert = alertstore.as_json()[0]

    assert alert["matched_indicator"] == indicator
    assert "matched_indicator" not in alert["event"]


def test_as_json_removes_nested_matched_indicator_when_parent_exists():
    event_indicator = {"value": "nested", "type": "processes"}
    alert_indicator = {"value": "parent", "type": "processes"}
    alertstore = AlertStore()
    alertstore.add(
        Alert(
            level=AlertLevel.CRITICAL,
            module="manifest",
            message="Matched indicator",
            event_time="2026-01-01 00:00:00",
            event={"path": "/tmp/example", "matched_indicator": event_indicator},
            matched_indicator=alert_indicator,
        )
    )

    alert = alertstore.as_json()[0]

    assert alert["matched_indicator"] == alert_indicator
    assert "matched_indicator" not in alert["event"]
