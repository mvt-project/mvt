# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import json
import logging

import pytest
from click.testing import CliRunner

from mvt.android.cli import check_intrusion_logs
from mvt.android.cmd_check_intrusion_logs import CmdAndroidCheckIntrusionLogs
from mvt.android.modules.intrusion_logs.base import IntrusionLogsModule
from mvt.android.modules.intrusion_logs.security_event import SecurityEvent
from mvt.common.alerts import AlertLevel


def _write_ndjson(path, records):
    path.write_text(
        "\n".join(json.dumps(record) for record in records),
        encoding="utf-8",
    )


def test_load_all_events_preserves_unknown_top_level_event(tmp_path):
    _write_ndjson(
        tmp_path / "intrusion.txt",
        [
            {
                "future_event": {
                    "event_time": 1_700_000_000_000,
                    "field": "value",
                }
            }
        ],
    )

    module = IntrusionLogsModule(target_path=str(tmp_path))
    events = module.load_all_events(str(tmp_path))

    assert events == {
        "future_event": [
            {
                "event_time": 1_700_000_000_000,
                "field": "value",
            }
        ]
    }


def test_check_intrusion_logs_warns_about_unknown_top_level_event_type(
    tmp_path, caplog
):
    _write_ndjson(
        tmp_path / "intrusion.txt",
        [
            {
                "future_event": {
                    "event_time": 1_700_000_000_000,
                    "field": "value",
                }
            }
        ],
    )

    with caplog.at_level(logging.WARNING):
        cmd = CmdAndroidCheckIntrusionLogs(target_path=str(tmp_path))
        cmd.run()

    assert "Found unknown intrusion logging event type(s): future_event" in caplog.text
    assert "Please open an issue on GitHub" in caplog.text


def test_check_intrusion_logs_parses_core_and_unknown_security_events(
    tmp_path, caplog
):
    _write_ndjson(
        tmp_path / "intrusion.txt",
        [
            {
                "dns_event": {
                    "event_time": 1_700_000_000_000,
                    "hostname": "example.com",
                    "package_name": "com.example.app",
                    "ip_addresses": ["/1.2.3.4"],
                }
            },
            {
                "connect_event": {
                    "event_time": 1_700_000_001_000,
                    "ip_address": "/5.6.7.8",
                    "port": 443,
                    "package_name": "com.example.app",
                }
            },
            {
                "security_event": {
                    "event_time": 1_700_000_002_000_000_000,
                    "app_process_start": {
                        "process": "com.example.app",
                        "uid": 10_000,
                        "pid": 1234,
                    },
                }
            },
            {
                "security_event": {
                    "event_time": 1_700_000_003_000_000_000,
                    "future_google_event": {
                        "field": "value",
                    },
                }
            },
        ],
    )

    with caplog.at_level(logging.WARNING):
        cmd = CmdAndroidCheckIntrusionLogs(target_path=str(tmp_path))
        cmd.run()

    assert [module.__class__.__name__ for module in cmd.executed] == [
        "DnsEvent",
        "ConnectEvent",
        "SecurityEvent",
    ]
    assert [len(module.results) for module in cmd.executed] == [1, 1, 2]

    security_module = next(
        module for module in cmd.executed if isinstance(module, SecurityEvent)
    )
    assert security_module.event_type_counts["app_process_start"] == 1
    assert security_module.event_type_counts["future_google_event"] == 1

    future_timeline_events = [
        event for event in cmd.timeline if event["event"] == "future_google_event"
    ]
    assert len(future_timeline_events) == 1
    assert "future_google_event" in future_timeline_events[0]["data"]
    assert "field" in future_timeline_events[0]["data"]
    assert (
        "Found unknown intrusion logging security event type(s): future_google_event"
        in caplog.text
    )
    assert "Please open an issue on GitHub" in caplog.text


def test_check_intrusion_logs_treats_event_id_as_security_event_metadata(
    tmp_path, caplog
):
    _write_ndjson(
        tmp_path / "intrusion.txt",
        [
            {
                "security_event": {
                    "event_id": 191,
                    "event_time": 1_700_000_002_000_000_000,
                    "keyguard_dismiss_auth_attempt": {
                        "success": True,
                        "method_strength": 0,
                    },
                }
            },
            {
                "security_event": {
                    "event_id": 192,
                    "event_time": 1_700_000_003_000_000_000,
                    "keyguard_dismissed": {},
                }
            },
        ],
    )

    with caplog.at_level(logging.WARNING):
        cmd = CmdAndroidCheckIntrusionLogs(target_path=str(tmp_path))
        cmd.run()

    security_module = next(
        module for module in cmd.executed if isinstance(module, SecurityEvent)
    )
    assert security_module.event_type_counts == {
        "keyguard_dismiss_auth_attempt": 1,
        "keyguard_dismissed": 1,
    }
    assert [event["event_id"] for event in security_module.results] == [191, 192]

    keyguard_events = {
        event["event"]: event
        for event in cmd.timeline
        if event["event"]
        in {"keyguard_dismiss_auth_attempt", "keyguard_dismissed"}
    }
    assert "Auth attempt: Success" in keyguard_events[
        "keyguard_dismiss_auth_attempt"
    ]["data"]
    assert keyguard_events["keyguard_dismissed"]["data"] == "Keyguard dismissed"
    assert "unknown intrusion logging security event type(s): event_id" not in caplog.text


def test_check_intrusion_logs_cli_lists_modules(tmp_path):
    _write_ndjson(tmp_path / "intrusion.txt", [])

    result = CliRunner().invoke(check_intrusion_logs, ["--list-modules", str(tmp_path)])

    assert result.exit_code == 0
    assert "DnsEvent" in result.output
    assert "ConnectEvent" in result.output
    assert "SecurityEvent" in result.output


def _run_security_heuristics(results):
    # No indicators loaded: heuristic alerts must still fire.
    module = SecurityEvent(results=results)
    module.check_indicators()
    return module.alertstore.alerts


def test_cert_authority_installed_raises_medium_alert_without_indicators():
    alerts = _run_security_heuristics(
        [
            {
                "timestamp": "2024-01-01 00:00:00.000",
                "cert_authority_installed": {
                    "subject": "CN=Unexpected Root CA",
                    "success": True,
                },
            }
        ]
    )

    assert len(alerts) == 1
    assert alerts[0].level == AlertLevel.MEDIUM
    assert "Certificate authority installed" in alerts[0].message
    assert "Unexpected Root CA" in alerts[0].message


# Exported logs encode success as a JSON bool, raw SecurityLog as int 0/1.
@pytest.mark.parametrize("success", [False, 0])
def test_failed_cert_authority_install_does_not_alert(success, caplog):
    with caplog.at_level(logging.WARNING):
        alerts = _run_security_heuristics(
            [
                {
                    "timestamp": "2024-01-01 00:00:00.000",
                    "cert_authority_installed": {
                        "subject": "CN=Unexpected Root CA",
                        "success": success,
                    },
                }
            ]
        )

    assert alerts == []
    assert "Failed certificate authority install attempt" in caplog.text
    assert "Unexpected Root CA" in caplog.text


def test_cert_validation_failure_raises_medium_alert_without_indicators():
    alerts = _run_security_heuristics(
        [
            {
                "timestamp": "2024-01-01 00:00:00.000",
                "cert_validation_failure": "chain validation failed",
            }
        ]
    )

    assert len(alerts) == 1
    assert alerts[0].level == AlertLevel.MEDIUM
    assert "Certificate validation failure" in alerts[0].message


def test_security_heuristics_fire_when_no_indicators_loaded():
    # check_indicators() previously returned early with no indicators loaded,
    # so none of the heuristic alerts fired on a default run.
    alerts = _run_security_heuristics(
        [
            {"timestamp": "2024-01-01 00:00:00.000", "wipe_failure": {"reason": "x"}},
            {
                "timestamp": "2024-01-01 00:00:00.000",
                "key_integrity_violation": {"key_id": "k1"},
            },
        ]
    )

    assert len(alerts) == 2
    assert all(alert.level == AlertLevel.MEDIUM for alert in alerts)
