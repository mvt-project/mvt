# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import json
import logging
from pathlib import Path

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


def test_check_intrusion_logs_parses_core_and_unknown_security_events(tmp_path, caplog):
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
        if event["event"] in {"keyguard_dismiss_auth_attempt", "keyguard_dismissed"}
    }
    assert (
        "Auth attempt: Success"
        in keyguard_events["keyguard_dismiss_auth_attempt"]["data"]
    )
    assert keyguard_events["keyguard_dismissed"]["data"] == "Keyguard dismissed"
    assert (
        "unknown intrusion logging security event type(s): event_id" not in caplog.text
    )


def test_check_intrusion_logs_cli_lists_modules(tmp_path):
    _write_ndjson(tmp_path / "intrusion.txt", [])

    result = CliRunner().invoke(check_intrusion_logs, ["--list-modules", str(tmp_path)])

    assert result.exit_code == 0
    assert "DnsEvent" in result.output
    assert "ConnectEvent" in result.output
    assert "SecurityEvent" in result.output


@pytest.mark.parametrize("success", [True, False, 1, 0])
def test_check_intrusion_logs_recognizes_key_imported_events(tmp_path, caplog, success):
    key_info = {
        "success": success,
        "key_id": "example_key",
        "uid": -2147483545,
    }
    _write_ndjson(
        tmp_path / "intrusion.txt",
        [
            {
                "security_event": {
                    "event_id": 0,
                    "event_time": 1_700_000_002_000_000_000,
                    "key_imported": key_info,
                }
            }
        ],
    )

    with caplog.at_level(logging.INFO):
        cmd = CmdAndroidCheckIntrusionLogs(target_path=str(tmp_path))
        cmd.run()

    security_module = next(
        module for module in cmd.executed if isinstance(module, SecurityEvent)
    )
    assert security_module.event_type_counts == {"key_imported": 1}
    assert len(security_module.results) == 1
    assert security_module.results[0]["key_imported"] == key_info
    assert security_module.results[0]["event_id"] == 0
    assert cmd.timeline == [
        {
            "timestamp": security_module.results[0]["timestamp"],
            "module": "SecurityEvent",
            "event": "key_imported",
            "data": f"Key {'imported' if success else 'import failed'}: example_key",
        }
    ]
    assert cmd.timeline[0]["timestamp"] is not None
    assert "Key Import" in caplog.text
    assert "Found unknown intrusion logging security event type(s)" not in caplog.text
    assert security_module.alertstore.alerts == []


def test_check_intrusion_logs_exported_event_schemas(caplog):
    # Field names/types from issue #971's Pixel export, with illustrative values.
    fixture_dir = Path(__file__).parents[1] / "artifacts/android_data/intrusion_logs"
    with caplog.at_level(logging.WARNING):
        cmd = CmdAndroidCheckIntrusionLogs(target_path=str(fixture_dir))
        cmd.run()

    assert [len(module.results) for module in cmd.executed] == [1, 1, 18]
    assert {event["timestamp"] for event in cmd.timeline} == {
        "2023-11-14 22:13:20.000000"
    }
    assert {event["event"]: event["data"] for event in cmd.timeline} == {
        "dns_query": "DNS query for example.com by com.example.app [IPs: 192.0.2.1]",
        "network_connection": "Connection to 192.0.2.1:443 by com.example.app",
        "adb_shell_cmd": "ADB shell command: com.example.app",
        "adb_sync_recv_file": "File pulled via ADB: /sdcard/Download/example.txt",
        "adb_sync_send_file": "File pushed via ADB: /sdcard/Download/example.txt",
        "app_process_start": "Process started: com.example.app (UID: 10000, PID: 1234)",
        "keyguard_dismissed": "Keyguard dismissed",
        "keyguard_dismiss_auth_attempt": "Auth attempt: Success (method strength: 0)",
        "keyguard_secured": "Device locked",
        "os_startup": "OS startup (verified boot: green, dm-verity: enforcing)",
        "logging_started": "Audit logging started",
        "key_generated": "Key generated: example_key (UID: 10000)",
        "key_imported": "Key imported: example_key",
        "key_destruction": "Key destroyed: example_key (UID: 10000)",
        "user_restriction_added": (
            "User restriction added by com.example.admin: no_install_apps"
        ),
        "user_restriction_removed": (
            "User restriction removed by com.example.admin: no_install_apps"
        ),
        "crypto_self_test_completed": "Crypto self test: passed",
        "package_installed": "Package Installed: com.example.app (v1, user: 0)",
        "package_updated": "Package Updated: com.example.app (v2, user: 0)",
        "package_uninstalled": "Package Uninstalled: com.example.app (v2, user: 0)",
    }
    # The summaries may select fields, but JSON results must retain every field.
    results = {
        record["event_id"]: record
        for module in cmd.executed
        for record in module.results
    }
    for line in (fixture_dir / "exported-events.txt").read_text().splitlines():
        original = next(iter(json.loads(line).values()))
        result = results[original["event_id"]]
        assert {key: result[key] for key in original} == original
    assert "Found unknown intrusion logging" not in caplog.text


def test_exported_adb_events_match_indicators(tmp_path, indicators_factory):
    _write_ndjson(
        tmp_path / "intrusion.txt",
        [
            {
                "security_event": {
                    "event_time": 1_700_000_000_000_000_000,
                    "adb_shell_cmd": {"command": "com.example.suspicious"},
                }
            },
            *[
                {
                    "security_event": {
                        "event_time": 1_700_000_000_000_000_000,
                        event: {"path": "/data/local/tmp/suspicious"},
                    }
                }
                for event in ("adb_sync_recv_file", "adb_sync_send_file")
            ],
        ],
    )
    cmd = CmdAndroidCheckIntrusionLogs(
        target_path=str(tmp_path),
        iocs=indicators_factory(
            app_ids=["com.example.suspicious"],
            file_paths=["/data/local/tmp/suspicious"],
        ),
    )
    cmd.run()
    security_module = next(
        module for module in cmd.executed if isinstance(module, SecurityEvent)
    )
    alerts = security_module.alertstore.alerts
    assert len(alerts) == 3
    assert all(alert.level == AlertLevel.CRITICAL for alert in alerts)


def test_check_intrusion_logs_source_event_schemas(caplog):
    # Events absent from issue #971, verified in GMS 26.32.34's BackupService
    # and csza JSON serializers. Values are illustrative; see the format docs.
    fixture_dir = (
        Path(__file__).parents[1] / "artifacts/android_data/intrusion_logs_source"
    )
    with caplog.at_level(logging.WARNING):
        cmd = CmdAndroidCheckIntrusionLogs(target_path=str(fixture_dir))
        cmd.run()

    assert [len(module.results) for module in cmd.executed] == [0, 0, 28]
    assert {event["timestamp"] for event in cmd.timeline} == {
        "2023-11-14 22:13:20.000000"
    }
    assert {event["event"]: event["data"] for event in cmd.timeline} == {
        "adb_shell_interactive": "ADB interactive shell opened",
        "os_shutdown": "OS shutdown",
        "logging_stopped": "Audit logging stopped",
        "media_mounted": "Media mounted: /storage/example (Example)",
        "media_unmounted": "Media unmounted: /storage/example (Example)",
        "log_buffer_size_critical": "Log buffer at 90% capacity",
        "password_expiration_set": "Password expiration set by com.example.admin: 0ms",
        "password_complexity_set": "Password complexity set by com.example.admin",
        "password_history_length_set": "Password history length set by com.example.admin: 5",
        "max_screen_lock_timeout_set": "Max screen lock timeout set by com.example.admin: 60000ms",
        "max_password_attempts_set": "Max password attempts set by com.example.admin: 0",
        "keyguard_disabled_features_set": "Keyguard features disabled by com.example.admin: 0",
        "remote_lock": "Device remotely locked by com.example.admin",
        "wipe_failure": "Device wipe failed",
        "cert_authority_installed": "Cert installed: CN=Example CA",
        "cert_authority_removed": "Cert removed: CN=Example CA",
        "key_integrity_violation": "Key integrity violation: example_key",
        "cert_validation_failure": "Certificate validation failure: chain validation failed",
        "camera_policy_set": "Camera enabled by com.example.admin",
        "password_complexity_required": "Password complexity required by com.example.admin: 0",
        "password_changed": "Password changed (complexity: 0, user: 10)",
        "wifi_connection": "WiFi connection: connected (BSSID: 02:00:00:00:00:01) - example reason",
        "wifi_disconnection": "WiFi disconnection (BSSID: 02:00:00:00:00:01) - example reason",
        "bluetooth_connection": "Bluetooth connected: 02:00:00:00:00:02 - example reason",
        "bluetooth_disconnection": "Bluetooth disconnected: 02:00:00:00:00:02 - example reason",
        "backup_service_toggled": "Backup service disabled by com.example.admin",
        "nfc_enabled": "NFC enabled",
        "nfc_disabled": "NFC disabled",
    }
    security_module = next(
        module for module in cmd.executed if isinstance(module, SecurityEvent)
    )
    originals = [
        json.loads(line)["security_event"]
        for line in (fixture_dir / "exported-events.txt").read_text().splitlines()
    ]
    for original, result in zip(originals, security_module.results):
        assert {key: result[key] for key in original} == original
    assert "Found unknown intrusion logging" not in caplog.text
    assert len(security_module.alertstore.alerts) == 4
    assert all(
        alert.level == AlertLevel.MEDIUM for alert in security_module.alertstore.alerts
    )


@pytest.mark.parametrize(
    ("event", "payload", "expected"),
    [
        (
            "os_startup",
            {"verified_boot_state": "green", "dm_verity_mode": "enforcing"},
            "OS startup (verified boot: green, dm-verity: enforcing)",
        ),
        *[
            (
                event,
                {"mount_point": "/storage/example", "volume_label": "Example"},
                f"Media {action}: /storage/example (Example)",
            )
            for event, action in (
                ("media_mount", "mounted"),
                ("media_unmount", "unmounted"),
            )
        ],
        (
            "password_expiration_set",
            {"admin_package": "com.example.admin", "timeout_ms": 60000},
            "Password expiration set by com.example.admin: 60000ms",
        ),
        (
            "max_screen_lock_timeout_set",
            {"admin_package": "com.example.admin", "timeout_ms": 60000},
            "Max screen lock timeout set by com.example.admin: 60000ms",
        ),
        (
            "max_password_attempts_set",
            {"admin_package": "com.example.admin", "max_attempts": 5},
            "Max password attempts set by com.example.admin: 5",
        ),
        (
            "keyguard_disabled_features_set",
            {"admin_package": "com.example.admin", "disabled_features": 0},
            "Keyguard features disabled by com.example.admin: 0",
        ),
        (
            "password_changed",
            {"complexity": 0, "user_id": 10},
            "Password changed (complexity: 0, user: 10)",
        ),
        *[
            (
                event,
                {"mac_address": "02:00:00:00:00:02", "success": True},
                f"Bluetooth {action}: 02:00:00:00:00:02",
            )
            for event, action in (
                ("bluetooth_connection", "connected"),
                ("bluetooth_disconnection", "disconnected"),
            )
        ],
        *[
            (
                f"user_restriction_{action}",
                {
                    "admin_package": "com.example.admin",
                    "restriction": "no_install_apps",
                },
                f"User restriction {action} by com.example.admin: no_install_apps",
            )
            for action in ("added", "removed")
        ],
    ],
)
def test_security_event_legacy_payload_fields(event, payload, expected):
    assert SecurityEvent().serialize({event: payload})["data"] == expected


def test_exported_fields_take_precedence_over_legacy_fields():
    record = {
        "password_expiration_set": {
            "package": "com.example.admin",
            "admin_package": "legacy.admin",
            "timeout": 0,
            "timeout_ms": 60000,
        }
    }
    assert SecurityEvent().serialize(record)["data"] == (
        "Password expiration set by com.example.admin: 0ms"
    )


def _run_security_heuristics(results):
    # No indicators loaded: heuristic alerts must still fire.
    module = SecurityEvent(results=results)
    module.check_indicators()
    return module.alertstore.alerts


@pytest.mark.parametrize("success", [False, 0])
def test_known_pinstorage_key_generation_failure_does_not_warn(success, caplog):
    record = {
        "timestamp": "2026-06-17 15:31:02.014",
        "key_generated": {
            "success": success,
            "key_id": "PinStorage_crossReboot_key",
            "uid": 1001,
        },
    }

    with caplog.at_level(logging.WARNING):
        _run_security_heuristics([record])

    assert "Failed key generation detected" not in caplog.text

    timeline_event = SecurityEvent().serialize(record)
    assert timeline_event["event"] == "key_generated"
    assert "Key generation failed: PinStorage_crossReboot_key" in timeline_event["data"]


@pytest.mark.parametrize(
    ("key_id", "uid"),
    [
        ("PinStorage_crossReboot_key", 10_000),
        ("another_key", 1001),
    ],
)
def test_other_key_generation_failures_still_warn(key_id, uid, caplog):
    with caplog.at_level(logging.WARNING):
        _run_security_heuristics(
            [
                {
                    "timestamp": "2026-06-17 15:31:02.014",
                    "key_generated": {
                        "success": False,
                        "key_id": key_id,
                        "uid": uid,
                    },
                }
            ]
        )

    assert f"Failed key generation detected for key_id: {key_id}" in caplog.text


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
