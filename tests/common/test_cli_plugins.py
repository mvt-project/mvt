from types import SimpleNamespace

import click
from click.testing import CliRunner

from mvt.common.cli_plugins import (
    ANDROID_CLI_PLUGIN_GROUP,
    IOS_CLI_PLUGIN_GROUP,
    BrokenPluginCommand,
    load_cli_commands_option,
    register_cli_commands_from_path,
    register_cli_plugins,
    register_installed_cli_commands,
)


COMMAND_TEMPLATE = """
import click


@click.command({name!r})
@click.pass_context
def cli(ctx):
    click.echo({message!r})
    if ctx.obj:
        click.echo(ctx.obj.get("marker", ""))
"""


def _write_command(path, name, message="command ran"):
    path.write_text(
        COMMAND_TEMPLATE.format(name=name, message=message),
        encoding="utf-8",
    )
    return path


def _make_group():
    @click.group()
    @load_cli_commands_option
    @click.pass_context
    def group(ctx):
        ctx.ensure_object(dict)
        ctx.obj["marker"] = "parent context"

    return group


def _entry_point(name, value, command=None, exception=None, distribution="plugin"):
    def load():
        if exception is not None:
            raise exception
        return command

    dist = SimpleNamespace(metadata={"Name": distribution}, version="1.0")
    return SimpleNamespace(name=name, value=value, load=load, dist=dist)


def test_load_command_option_registers_command_before_resolution(tmp_path):
    command_path = _write_command(tmp_path / "hello.py", "hello")
    group = _make_group()

    result = CliRunner().invoke(
        group,
        ["--load-command", str(command_path), "hello"],
    )

    assert result.exit_code == 0
    assert "command ran" in result.output
    assert "parent context" in result.output


def test_load_command_option_supports_folders_and_repeated_paths(tmp_path):
    folder = tmp_path / "commands"
    folder.mkdir()
    _write_command(folder / "b.py", "second")
    _write_command(folder / "a.py", "first")
    _write_command(folder / ".hidden.py", "hidden")
    _write_command(folder / "__init__.py", "init")
    other = _write_command(tmp_path / "third.py", "third")
    group = _make_group()

    result = CliRunner().invoke(
        group,
        [
            "--load-command",
            str(folder),
            "--load-command",
            str(other),
            "--load-command",
            str(other),
            "--help",
        ],
    )

    assert result.exit_code == 0
    assert "first" in result.output
    assert "second" in result.output
    assert "third" in result.output
    assert "hidden" not in result.output
    assert "init" not in result.output


def test_loaded_command_participates_in_shell_completion(tmp_path):
    command_path = _write_command(tmp_path / "hello.py", "hello")
    group = _make_group()
    words = f"group --load-command {command_path} he"

    result = CliRunner().invoke(
        group,
        [],
        env={
            "_GROUP_COMPLETE": "bash_complete",
            "COMP_WORDS": words,
            "COMP_CWORD": "3",
        },
    )

    assert result.exit_code == 0
    assert "plain,hello" in result.output


def test_explicit_command_import_and_contract_failures_are_usage_errors(tmp_path):
    broken_path = tmp_path / "broken.py"
    broken_path.write_text("raise RuntimeError('broken import')", encoding="utf-8")
    missing_cli_path = tmp_path / "missing_cli.py"
    missing_cli_path.write_text("value = 1", encoding="utf-8")

    broken_result = CliRunner().invoke(
        _make_group(),
        ["--load-command", str(broken_path), "broken"],
    )
    missing_cli_result = CliRunner().invoke(
        _make_group(),
        ["--load-command", str(missing_cli_path), "missing-cli"],
    )

    assert broken_result.exit_code == 2
    assert "broken import" in broken_result.output
    assert missing_cli_result.exit_code == 2
    assert "must export a Click command or group named 'cli'" in (
        missing_cli_result.output
    )


def test_environment_command_failure_gets_broken_placeholder(tmp_path):
    command_path = tmp_path / "broken_command.py"
    command_path.write_text("raise RuntimeError('broken import')", encoding="utf-8")
    group = click.Group()

    registered = register_cli_commands_from_path(group, command_path)

    assert registered == ["broken-command"]
    assert isinstance(group.commands["broken-command"], BrokenPluginCommand)
    result = CliRunner().invoke(group, ["broken-command"])
    assert result.exit_code == 1
    assert "broken import" in result.output
    assert str(command_path) in result.output


def test_environment_command_system_exit_gets_broken_placeholder(tmp_path):
    command_path = tmp_path / "exiting_command.py"
    command_path.write_text("raise SystemExit(7)", encoding="utf-8")
    group = click.Group()

    registered = register_cli_commands_from_path(group, command_path)

    assert registered == ["exiting-command"]
    assert isinstance(group.commands["exiting-command"], BrokenPluginCommand)
    result = CliRunner().invoke(group, ["exiting-command"])
    assert result.exit_code == 1
    assert "Unable to import custom command" in result.output
    assert result.output.rstrip().endswith(": 7")


def test_installed_entry_point_name_is_the_command_name(monkeypatch):
    @click.command("internal-name")
    def command():
        click.echo("installed command ran")

    entry_point = _entry_point(
        "external-name",
        "example_plugin:cli",
        command=command,
    )
    monkeypatch.setattr(
        "mvt.common.cli_plugins.importlib.metadata.entry_points",
        lambda **kwargs: [entry_point],
    )
    group = click.Group()

    registered = register_installed_cli_commands(group, IOS_CLI_PLUGIN_GROUP)

    assert registered == ["external-name"]
    assert "internal-name" not in group.commands
    result = CliRunner().invoke(group, ["external-name"])
    assert result.exit_code == 0
    assert result.output == "installed command ran\n"


def test_broken_installed_plugin_does_not_break_cli(monkeypatch):
    broken = _entry_point(
        "broken",
        "broken_plugin:cli",
        exception=RuntimeError("missing dependency"),
        distribution="broken-plugin",
    )
    monkeypatch.setattr(
        "mvt.common.cli_plugins.importlib.metadata.entry_points",
        lambda **kwargs: [broken],
    )
    group = click.Group()

    register_installed_cli_commands(group, IOS_CLI_PLUGIN_GROUP)

    help_result = CliRunner().invoke(group, ["--help"])
    assert help_result.exit_code == 0
    assert "Warning: external command could not be loaded." in help_result.output

    result = CliRunner().invoke(group, ["broken"])
    assert result.exit_code == 1
    assert "broken-plugin 1.0 (broken_plugin:cli)" in result.output
    assert "RuntimeError: missing dependency" in result.output


def test_installed_plugin_system_exit_does_not_break_cli(monkeypatch):
    exiting = _entry_point(
        "exiting",
        "exiting_plugin:cli",
        exception=SystemExit(7),
        distribution="exiting-plugin",
    )
    monkeypatch.setattr(
        "mvt.common.cli_plugins.importlib.metadata.entry_points",
        lambda **kwargs: [exiting],
    )
    group = click.Group()

    register_installed_cli_commands(group, IOS_CLI_PLUGIN_GROUP)

    help_result = CliRunner().invoke(group, ["--help"])
    assert help_result.exit_code == 0
    result = CliRunner().invoke(group, ["exiting"])
    assert result.exit_code == 1
    assert "SystemExit: 7" in result.output


def test_non_click_entry_point_gets_broken_placeholder(monkeypatch):
    invalid = _entry_point("invalid", "plugin:value", command=object())
    monkeypatch.setattr(
        "mvt.common.cli_plugins.importlib.metadata.entry_points",
        lambda **kwargs: [invalid],
    )
    group = click.Group()

    register_installed_cli_commands(group, IOS_CLI_PLUGIN_GROUP)

    assert isinstance(group.commands["invalid"], BrokenPluginCommand)
    result = CliRunner().invoke(group, ["invalid"])
    assert result.exit_code == 1
    assert "must resolve to a Click command or group" in result.output


def test_entry_point_discovery_failure_does_not_break_group(monkeypatch, caplog):
    def fail_discovery(**kwargs):
        raise RuntimeError("invalid package metadata")

    monkeypatch.setattr(
        "mvt.common.cli_plugins.importlib.metadata.entry_points",
        fail_discovery,
    )
    group = click.Group()

    registered = register_installed_cli_commands(group, IOS_CLI_PLUGIN_GROUP)

    assert registered == []
    assert not group.commands
    assert "Unable to discover external commands" in caplog.text
    assert "invalid package metadata" in caplog.text


def test_builtin_and_first_external_command_win_collisions(monkeypatch, caplog):
    @click.command("version")
    def core_version():
        pass

    @click.command()
    def first():
        pass

    @click.command()
    def second():
        pass

    entry_points = [
        _entry_point("duplicate", "z_plugin:cli", command=second, distribution="z"),
        _entry_point("version", "plugin:version", command=first),
        _entry_point("duplicate", "a_plugin:cli", command=first, distribution="a"),
    ]
    monkeypatch.setattr(
        "mvt.common.cli_plugins.importlib.metadata.entry_points",
        lambda **kwargs: entry_points,
    )
    group = click.Group(commands={"version": core_version})

    registered = register_installed_cli_commands(group, IOS_CLI_PLUGIN_GROUP)

    assert registered == ["duplicate"]
    assert group.commands["version"] is core_version
    assert group.commands["duplicate"] is first
    assert "the command name is already registered" in caplog.text


def test_explicit_command_cannot_replace_existing_command(tmp_path):
    command_path = _write_command(tmp_path / "version.py", "version")
    group = _make_group()

    @group.command("version")
    def core_version():
        pass

    result = CliRunner().invoke(
        group,
        ["--load-command", str(command_path), "version"],
    )

    assert result.exit_code == 2
    assert "the command name is already registered" in result.output


def test_platform_entry_point_groups_and_environment_paths_are_separate(
    tmp_path, monkeypatch
):
    ios_path = _write_command(tmp_path / "ios.py", "ios-file")
    android_path = _write_command(tmp_path / "android.py", "android-file")

    @click.command()
    def ios_package():
        pass

    @click.command()
    def android_package():
        pass

    def entry_points(*, group):
        if group == IOS_CLI_PLUGIN_GROUP:
            return [_entry_point("ios-package", "ios_plugin:cli", ios_package)]
        return [_entry_point("android-package", "android_plugin:cli", android_package)]

    monkeypatch.setattr(
        "mvt.common.cli_plugins.importlib.metadata.entry_points",
        entry_points,
    )
    monkeypatch.setenv("TEST_IOS_COMMANDS", str(ios_path))
    monkeypatch.setenv("TEST_ANDROID_COMMANDS", str(android_path))
    ios_group = click.Group()
    android_group = click.Group()

    register_cli_plugins(
        ios_group,
        entry_point_group=IOS_CLI_PLUGIN_GROUP,
        environment_variable="TEST_IOS_COMMANDS",
    )
    register_cli_plugins(
        android_group,
        entry_point_group=ANDROID_CLI_PLUGIN_GROUP,
        environment_variable="TEST_ANDROID_COMMANDS",
    )

    assert set(ios_group.commands) == {"ios-file", "ios-package"}
    assert set(android_group.commands) == {"android-file", "android-package"}
