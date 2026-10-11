# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

import pytest
from click.testing import CliRunner

from mvt.android.cli import cli as android_cli
from mvt.cli import cli as mvt_cli
from mvt.common.log import MVTLogHandler
from mvt.common.utils import set_verbose_logging
from mvt.ios.cli import cli as ios_cli

# Keep the banner of the group callback from checking for updates online.
OFFLINE = ["--disable-update-check", "--disable-indicator-update-check"]

PROGRAMS = {"mvt": mvt_cli, "mvt-ios": ios_cli, "mvt-android": android_cli}


@pytest.fixture(autouse=True)
def _reset_console_level():
    """Leave the console handler at its default level after every test."""
    yield
    set_verbose_logging(False)


def _console_level():
    """Return the level of MVT's own console log handler."""
    for handler in logging.getLogger("mvt").handlers:
        if isinstance(handler, MVTLogHandler):
            return handler.level
    raise AssertionError("MVT has no console log handler")


class TestVerboseOnTheCommands:
    @pytest.mark.parametrize("program", sorted(PROGRAMS))
    def test_verbose_before_the_command_name_turns_on_debug(self, program):
        cli = PROGRAMS[program]

        result = CliRunner().invoke(cli, [*OFFLINE, "--verbose", "version"])

        assert result.exit_code == 0
        assert _console_level() == logging.DEBUG

    @pytest.mark.parametrize("program", sorted(PROGRAMS))
    def test_a_run_without_verbose_goes_back_to_info(self, program):
        cli = PROGRAMS[program]
        CliRunner().invoke(cli, [*OFFLINE, "--verbose", "version"])

        result = CliRunner().invoke(cli, [*OFFLINE, "version"])

        assert result.exit_code == 0
        assert _console_level() == logging.INFO

    def test_mvt_verbose_without_a_command_prints_the_help(self):
        result = CliRunner().invoke(mvt_cli, [*OFFLINE, "--verbose"])

        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert _console_level() == logging.DEBUG


class TestVerboseOnTheCheckCommands:
    def test_ios_command_default_does_not_undo_the_cli_choice(self, tmp_path):
        result = CliRunner().invoke(
            ios_cli,
            [*OFFLINE, "--verbose", "check-backup", "--list-modules", str(tmp_path)],
        )

        assert result.exit_code == 0
        assert _console_level() == logging.DEBUG

    def test_ios_verbose_after_the_command_name_still_works(self, tmp_path):
        result = CliRunner().invoke(
            ios_cli,
            [*OFFLINE, "check-backup", "--verbose", "--list-modules", str(tmp_path)],
        )

        assert result.exit_code == 0
        assert _console_level() == logging.DEBUG

    def test_android_command_default_does_not_undo_the_cli_choice(self, tmp_path):
        result = CliRunner().invoke(
            android_cli,
            [*OFFLINE, "--verbose", "check-bugreport", "--list-modules", str(tmp_path)],
        )

        assert result.exit_code == 0
        assert _console_level() == logging.DEBUG

    def test_android_verbose_after_the_command_name_still_works(self, tmp_path):
        result = CliRunner().invoke(
            android_cli,
            [*OFFLINE, "check-bugreport", "--verbose", "--list-modules", str(tmp_path)],
        )

        assert result.exit_code == 0
        assert _console_level() == logging.DEBUG

    def test_the_command_option_says_it_is_kept_for_compatibility(self):
        result = CliRunner().invoke(ios_cli, [*OFFLINE, "check-backup", "--help"])

        assert result.exit_code == 0
        assert "kept for compatibility" in result.output
