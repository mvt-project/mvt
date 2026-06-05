# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import json
import logging

from click.testing import CliRunner

from mvt.android.cli import check_intrusion_logs
from mvt.android.cmd_check_intrusion_logs import CmdAndroidCheckIntrusionLogs
from mvt.android.modules.intrusion_logs.base import IntrusionLogsModule
from mvt.android.modules.intrusion_logs.security_event import SecurityEvent


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


def test_check_intrusion_logs_cli_lists_modules(tmp_path):
    _write_ndjson(tmp_path / "intrusion.txt", [])

    result = CliRunner().invoke(check_intrusion_logs, ["--list-modules", str(tmp_path)])

    assert result.exit_code == 0
    assert "DnsEvent" in result.output
    assert "ConnectEvent" in result.output
    assert "SecurityEvent" in result.output
