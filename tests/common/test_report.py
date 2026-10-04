# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2025 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import json
import os
import re

from click.testing import CliRunner

from mvt.android.cli import cli as android_cli
from mvt.common.report import REPORT_FILE_NAME, collect_report_data, generate_report
from mvt.ios.cli import cli as ios_cli

OFFLINE = ["--disable-update-check", "--disable-indicator-update-check"]


def _write(path, name, content):
    with open(os.path.join(path, name), "w", encoding="utf-8", newline="") as handle:
        if isinstance(content, str):
            handle.write(content)
        else:
            json.dump(content, handle)


def _results(tmp_path):
    path = str(tmp_path / "results")
    os.makedirs(path)
    _write(
        path,
        "info.json",
        {
            "target_path": "/cases/backup",
            "mvt_version": "2.0.0",
            "date": "2026-01-02 10:00:00.000000",
            "ioc_files": ["/iocs/test.stix2"],
            "hashes": [],
        },
    )
    _write(
        path,
        "alerts.json",
        [
            {
                "level": "CRITICAL",
                "module": "sms",
                "message": "Found a known suspicious domain",
                "event_time": "",
                "event": {
                    "text": "</script><script>alert(1)</script>",
                    "isodate": "2021-01-01 12:00:00.000000",
                },
                "matched_indicator": {
                    "value": "example.org",
                    "type": "domains",
                    "name": "TestMalware",
                    "stix2_file_name": "test.stix2",
                },
            },
            {
                "level": "LOW",
                "module": "datausage",
                "message": "Missing process",
                "event_time": "2021-01-01 11:59:00.000000",
                "event": {},
                "matched_indicator": None,
            },
        ],
    )
    _write(path, "sms.json", [{"text": "hello"}, {"text": "world"}])
    _write(path, "sms_detected.json", [])
    _write(
        path,
        "backup_info.json",
        {"Product Type": "iPhone9,3", "Product Version": "14.3", "IMEI": "42"},
    )
    # Timelines written on Windows carry an empty row after each line.
    _write(
        path,
        "timeline.csv",
        '"UTC Timestamp","Plugin","Event","Description"\r\r\n'
        '"2021-01-01 12:00:00.000000","SMS","sms_received","hello"\r\r\n'
        '"2021-01-01 12:05:00.000000","Manifest","M---","Library/SMS"\r\r\n',
    )
    return path


def _embedded_data(html):
    match = re.search(
        r'<script id="mvt-report-data" type="application/json">(.*?)</script>',
        html,
        re.S,
    )
    assert match
    return json.loads(match.group(1))


class TestReport:
    def test_collects_the_results_of_a_check(self, tmp_path):
        path = _results(tmp_path)
        data = collect_report_data(path, path)

        assert data["platform"] == "ios"
        assert data["info"]["mvt_version"] == "2.0.0"
        assert len(data["info_sha256"]) == 64
        assert data["timeline"]["timezone"] == "UTC"
        assert [row[1] for row in data["timeline"]["rows"]] == ["SMS", "Manifest"]
        assert data["modules"] == [
            {
                "name": "backup_info",
                "file": "backup_info.json",
                "records": 3,
                "detections": 0,
            },
            {"name": "sms", "file": "sms.json", "records": 2, "detections": 1},
            {"name": "datausage", "file": None, "records": 0, "detections": 1},
        ]

    def test_leaves_device_identifiers_out(self, tmp_path):
        data = collect_report_data(_results(tmp_path), str(tmp_path))

        assert ["Model", "iPhone9,3"] in data["device"]
        assert "42" not in json.dumps(data["device"])

    def test_takes_the_time_of_the_record_when_an_alert_has_none(self, tmp_path):
        alerts = collect_report_data(_results(tmp_path), str(tmp_path))["alerts"]

        assert alerts[0]["time"] == "2021-01-01 12:00:00.000000"
        assert alerts[0]["time_source"] == "record"
        assert alerts[1]["time_source"] == "alert"

    def test_writes_a_self_contained_report(self, tmp_path):
        path = _results(tmp_path)
        report_path = generate_report(path)

        assert report_path == os.path.join(path, REPORT_FILE_NAME)
        with open(report_path, encoding="utf-8") as handle:
            html = handle.read()

        # Nothing is loaded from the network.
        assert not re.search(r'(src|href)="https?://', html)
        # A record cannot close the data element and run a script.
        assert "</script><script>alert(1)" not in html
        data = _embedded_data(html)
        assert (
            data["alerts"][0]["event"]["text"] == "</script><script>alert(1)</script>"
        )

    def test_links_to_the_results_from_another_folder(self, tmp_path):
        path = _results(tmp_path)
        report_path = generate_report(path, str(tmp_path / "out" / "case.html"))

        with open(report_path, encoding="utf-8") as handle:
            data = _embedded_data(handle.read())
        assert data["results_link"] == "../results"

    def test_report_command(self, tmp_path):
        path = _results(tmp_path)
        for cli in (ios_cli, android_cli):
            output = str(tmp_path / f"{cli.name}.html")
            result = CliRunner().invoke(cli, OFFLINE + ["report", "-o", output, path])

            assert result.exit_code == 0, result.output
            assert os.path.isfile(output)
