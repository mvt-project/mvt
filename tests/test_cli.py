# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from click.testing import CliRunner

from mvt.cli import cli
from mvt.common.updates import IndicatorsUpdates
from mvt.common.version import MVT_VERSION

# Keep the banner of the group callback from checking for updates online.
OFFLINE = ["--disable-update-check", "--disable-indicator-update-check"]


class TestMvtCommand:
    def test_running_mvt_alone_shows_the_logo_and_the_commands(self):
        result = CliRunner().invoke(cli, OFFLINE)

        assert result.exit_code == 0
        logo_at = result.output.index("Mobile Verification Toolkit")
        usage_at = result.output.index("Usage:")
        assert logo_at < usage_at
        assert "mvt-ios" in result.output and "mvt-android" in result.output

    def test_help_reminds_where_the_analysis_runs(self):
        result = CliRunner().invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "mvt-ios" in result.output
        assert "mvt-android" in result.output
        assert "check-*" in result.output

    def test_version_prints_the_installed_version(self):
        result = CliRunner().invoke(cli, [*OFFLINE, "version"])

        assert result.exit_code == 0
        assert f"Version: {MVT_VERSION}" in result.output

    def test_download_iocs_updates_the_indicators(self, monkeypatch):
        updates = []
        monkeypatch.setattr(
            IndicatorsUpdates, "update", lambda self: updates.append(self)
        )

        result = CliRunner().invoke(cli, [*OFFLINE, "download-iocs"])

        assert result.exit_code == 0
        assert len(updates) == 1
