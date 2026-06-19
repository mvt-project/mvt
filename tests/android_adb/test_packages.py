# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from click.testing import CliRunner

from mvt.android.cli import download_apks
from mvt.android.modules.adb import packages as packages_module
from mvt.android.modules.adb.packages import Packages


def test_check_virustotal_delays_after_missing_result(monkeypatch):
    lookups = []
    sleeps = []

    def fake_virustotal_lookup(file_hash):
        lookups.append(file_hash)
        if file_hash == "missing_hash":
            return None
        return {
            "attributes": {
                "last_analysis_stats": {"malicious": 0},
                "last_analysis_results": {},
            }
        }

    monkeypatch.setattr(packages_module, "virustotal_lookup", fake_virustotal_lookup)
    monkeypatch.setattr(packages_module.time, "sleep", sleeps.append)

    packages = [
        {
            "package_name": "org.example",
            "files": [
                {"path": "/data/app/missing.apk", "sha256": "missing_hash"},
                {"path": "/data/app/found.apk", "sha256": "found_hash"},
            ],
        }
    ]

    Packages.check_virustotal(packages, delay=16)

    assert lookups == ["missing_hash", "found_hash"]
    assert sleeps == [16]


def test_download_apks_rejects_negative_delay():
    runner = CliRunner()

    result = runner.invoke(download_apks, ["--delay", "-1"])

    assert result.exit_code == 2
    assert "Invalid value for '--delay'" in result.output
