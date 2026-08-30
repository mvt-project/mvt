# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import sys
from types import SimpleNamespace

import click
import pytest

import mvt.android
import mvt.cli
import mvt.ios
from mvt.android.cli import cli as android_cli
from mvt.android.cli import main as android_main
from mvt.cli import cli as mvt_cli
from mvt.cli import main as mvt_main
from mvt.common.cli_plugins import (
    ANDROID_CLI_PLUGIN_GROUP,
    IOS_CLI_PLUGIN_GROUP,
    MVT_ANDROID_CUSTOM_COMMANDS_ENV,
    MVT_CUSTOM_COMMANDS_ENV,
    MVT_IOS_CUSTOM_COMMANDS_ENV,
    NEUTRAL_CLI_PLUGIN_GROUP,
)
from mvt.ios.cli import cli as ios_cli
from mvt.ios.cli import main as ios_main

from .plugin_fixtures import (
    FIXTURE_COMMAND_NAME,
    run_isolated_python,
    write_cli_plugin_distribution,
)

MARKER_PLUGIN_TEMPLATE = """
import os

import click

# Touched when this module is imported, so a test can tell whether loading MVT
# executed the plugin.
open(os.environ["FIXTURE_PLUGIN_MARKER"], "a").close()


@click.command()
def cli():
    click.echo("fixture plugin ran")
"""

PROGRAMS = {
    "mvt": (mvt.cli, mvt_cli, NEUTRAL_CLI_PLUGIN_GROUP, MVT_CUSTOM_COMMANDS_ENV),
    "mvt-ios": (mvt.ios, ios_cli, IOS_CLI_PLUGIN_GROUP, MVT_IOS_CUSTOM_COMMANDS_ENV),
    "mvt-android": (
        mvt.android,
        android_cli,
        ANDROID_CLI_PLUGIN_GROUP,
        MVT_ANDROID_CUSTOM_COMMANDS_ENV,
    ),
}

CASE_SUMMARY_COMMAND = """
import click


@click.command("case-summary")
def cli():
    click.echo("case summary ran")
"""

# The entry-point group of another program, for each program: no group may add
# its commands to a CLI other than its own.
OTHER_PROGRAMS_GROUP = {
    "mvt": IOS_CLI_PLUGIN_GROUP,
    "mvt-ios": NEUTRAL_CLI_PLUGIN_GROUP,
    "mvt-android": NEUTRAL_CLI_PLUGIN_GROUP,
}


def _install_fixture_entry_point(monkeypatch, entry_point_group, command):
    def entry_points(*, group):
        if group != entry_point_group:
            return []
        return [
            SimpleNamespace(
                name=FIXTURE_COMMAND_NAME,
                value="fixture_cli_plugin:cli",
                load=lambda: command,
                dist=SimpleNamespace(
                    metadata={"Name": "fixture-cli-plugin"}, version="1.0"
                ),
            )
        ]

    monkeypatch.setattr(
        "mvt.common.cli_plugins.importlib.metadata.entry_points", entry_points
    )


def _offline_argv(program, *arguments):
    """Build an argument list which keeps the CLI from checking for updates."""
    return [
        program,
        "--disable-update-check",
        "--disable-indicator-update-check",
        *arguments,
    ]


@pytest.mark.parametrize("program", sorted(PROGRAMS))
def test_main_registers_installed_plugins_before_running_the_cli(
    program, monkeypatch, capsys, restore_cli_commands
):
    package, group, entry_point_group, _ = PROGRAMS[program]

    @click.command()
    def fixture_command():
        click.echo("fixture plugin ran")

    _install_fixture_entry_point(monkeypatch, entry_point_group, fixture_command)
    monkeypatch.setattr(sys, "argv", _offline_argv(program, FIXTURE_COMMAND_NAME))

    with pytest.raises(SystemExit) as exit_info:
        package.main()

    assert exit_info.value.code == 0
    assert "fixture plugin ran" in capsys.readouterr().out
    assert FIXTURE_COMMAND_NAME in group.commands


@pytest.mark.parametrize("program", sorted(PROGRAMS))
def test_main_completes_plugin_command_names(
    program, monkeypatch, capsys, restore_cli_commands
):
    package, _, entry_point_group, _ = PROGRAMS[program]

    @click.command()
    def fixture_command():
        pass

    _install_fixture_entry_point(monkeypatch, entry_point_group, fixture_command)
    complete_variable = f"_{program.upper().replace('-', '_')}_COMPLETE"
    monkeypatch.setenv(complete_variable, "bash_complete")
    monkeypatch.setenv("COMP_WORDS", f"{program} fixture")
    monkeypatch.setenv("COMP_CWORD", "1")
    monkeypatch.setattr(sys, "argv", [program])

    with pytest.raises(SystemExit):
        package.main()

    assert f"plain,{FIXTURE_COMMAND_NAME}" in capsys.readouterr().out


@pytest.mark.parametrize("program", sorted(PROGRAMS))
def test_main_still_loads_commands_from_a_file(
    program, monkeypatch, capsys, tmp_path, restore_cli_commands
):
    package, _, entry_point_group, _ = PROGRAMS[program]
    command_path = tmp_path / "case_summary.py"
    command_path.write_text(CASE_SUMMARY_COMMAND, encoding="utf-8")
    _install_fixture_entry_point(
        monkeypatch, entry_point_group, click.Command("unused")
    )
    monkeypatch.setattr(
        sys,
        "argv",
        _offline_argv(program, "--load-command", str(command_path), "case-summary"),
    )

    with pytest.raises(SystemExit) as exit_info:
        package.main()

    assert exit_info.value.code == 0
    assert "case summary ran" in capsys.readouterr().out


@pytest.mark.parametrize("program", sorted(PROGRAMS))
def test_main_loads_commands_from_the_environment_variable(
    program, monkeypatch, capsys, tmp_path, restore_cli_commands
):
    # Each CLI reads its own variable, so a main() reading another CLI's would
    # go unnoticed without this.
    package, _, _, environment_variable = PROGRAMS[program]
    command_path = tmp_path / "case_summary.py"
    command_path.write_text(CASE_SUMMARY_COMMAND, encoding="utf-8")
    monkeypatch.setenv(environment_variable, str(command_path))
    monkeypatch.setattr(sys, "argv", _offline_argv(program, "case-summary"))

    with pytest.raises(SystemExit) as exit_info:
        package.main()

    assert exit_info.value.code == 0
    assert "case summary ran" in capsys.readouterr().out


@pytest.mark.parametrize("program", sorted(PROGRAMS))
def test_main_ignores_the_entry_point_groups_of_the_other_programs(
    program, monkeypatch, capsys, restore_cli_commands
):
    package, group, _, _ = PROGRAMS[program]
    _install_fixture_entry_point(
        monkeypatch,
        OTHER_PROGRAMS_GROUP[program],
        click.Command(FIXTURE_COMMAND_NAME),
    )
    monkeypatch.setattr(sys, "argv", _offline_argv(program, "--help"))

    with pytest.raises(SystemExit) as exit_info:
        package.main()

    assert exit_info.value.code == 0
    assert FIXTURE_COMMAND_NAME not in group.commands
    assert FIXTURE_COMMAND_NAME not in capsys.readouterr().out


def test_the_console_script_targets_are_importable():
    # [project.scripts] points at these, so they must stay where they are.
    assert mvt.cli.main is mvt_main
    assert mvt.ios.main is ios_main
    assert mvt.android.main is android_main


def test_importing_mvt_does_not_import_a_cli(tmp_path):
    # The mvt package deliberately re-exports nothing of mvt.cli, so that
    # importing MVT stays cheap and free of side effects.
    result = run_isolated_python(
        "import sys\n"
        "import mvt\n"
        "print('imported a cli' if 'mvt.cli' in sys.modules else 'imported mvt')\n",
        home=tmp_path / "home",
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "imported mvt"


def test_importing_mvt_does_not_run_installed_plugins(tmp_path):
    site_path = write_cli_plugin_distribution(
        tmp_path / "site", IOS_CLI_PLUGIN_GROUP, MARKER_PLUGIN_TEMPLATE
    )
    marker = tmp_path / "plugin-imported"

    result = run_isolated_python(
        "import mvt.ios.cli\nimport mvt.android.cli\nprint('imported')",
        home=tmp_path / "home",
        site_path=site_path,
        FIXTURE_PLUGIN_MARKER=str(marker),
    )

    assert result.returncode == 0, result.stderr
    assert "imported" in result.stdout
    assert not marker.exists()


def test_registering_the_plugins_runs_the_entry_point(tmp_path):
    site_path = write_cli_plugin_distribution(
        tmp_path / "site", IOS_CLI_PLUGIN_GROUP, MARKER_PLUGIN_TEMPLATE
    )
    marker = tmp_path / "plugin-imported"

    result = run_isolated_python(
        "import click\n"
        "from mvt.common.cli_plugins import (\n"
        "    IOS_CLI_PLUGIN_GROUP,\n"
        "    BrokenPluginCommand,\n"
        "    register_installed_cli_commands,\n"
        ")\n"
        "group = click.Group()\n"
        "register_installed_cli_commands(group, IOS_CLI_PLUGIN_GROUP)\n"
        f"command = group.commands[{FIXTURE_COMMAND_NAME!r}]\n"
        "assert not isinstance(command, BrokenPluginCommand), command.help\n"
        "print('registered')\n",
        home=tmp_path / "home",
        site_path=site_path,
        FIXTURE_PLUGIN_MARKER=str(marker),
    )

    assert result.returncode == 0, result.stderr
    assert "registered" in result.stdout
    assert marker.exists()
