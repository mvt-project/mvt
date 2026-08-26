import json
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from mvt.android.cli import cli as android_cli
from mvt.cli import cli as mvt_cli
from mvt.common.cli_plugins import (
    ANDROID_CLI_PLUGIN_GROUP,
    IOS_CLI_PLUGIN_GROUP,
    NEUTRAL_CLI_PLUGIN_GROUP,
)
from mvt.common.cmd_plugins import plugins
from mvt.common.module import MVTModule
from mvt.common.module_loader import MODULES_ENTRY_POINT_GROUP
from mvt.common.updates import PluginUpdates
from mvt.ios.cli import cli as ios_cli


class ExampleModule(MVTModule):
    pass


class AnotherModule(MVTModule):
    pass


class FakeDistribution:
    def __init__(self, name, version="1.0.0", direct_url=None):
        self.name = name
        self.version = version
        self.direct_url = direct_url

    def read_text(self, file_name):
        if file_name == "direct_url.json" and self.direct_url is not None:
            return json.dumps(self.direct_url)
        return None


def _entry_point(name, distribution, modules=None, exception=None):
    def load():
        if exception is not None:
            raise exception
        return modules

    return SimpleNamespace(
        name=name, value="example_plugin:modules", dist=distribution, load=load
    )


def _run(command, arguments):
    # Keep rich from wrapping the table while its content is being asserted.
    return CliRunner().invoke(command, arguments, env={"COLUMNS": "200"})


def _table_rows(output):
    """Return the content of the table rows, without the header and the box."""
    return [
        [cell.strip() for cell in line.strip().strip("│").split("│")]
        for line in output.splitlines()
        if "│" in line
    ]


def _table_header(output):
    for line in output.splitlines():
        if "┃" in line:
            return [cell.strip() for cell in line.strip().strip("┃").split("┃")]
    return []


def _install(monkeypatch, distributions, entry_points):
    monkeypatch.setattr(
        "mvt.common.cmd_plugins.installed_plugin_distributions",
        lambda: distributions,
    )
    monkeypatch.setattr(
        "mvt.common.cmd_plugins.importlib.metadata.entry_points",
        lambda *, group: entry_points.get(group, []),
    )


def test_plugins_is_a_builtin_command_of_the_mvt_cli_only():
    assert mvt_cli.commands["plugins"] is plugins
    assert "plugins" not in ios_cli.commands
    assert "plugins" not in android_cli.commands


def test_list_shows_what_every_plugin_contributes(monkeypatch):
    index_plugin = FakeDistribution("example-plugin", version="1.2.0")
    repository_plugin = FakeDistribution(
        "repository-plugin",
        version="0.1.0",
        direct_url={
            "url": "https://example.org/plugin.git",
            "vcs_info": {"vcs": "git", "commit_id": "b" * 40},
        },
    )
    local_plugin = FakeDistribution(
        "local-plugin",
        direct_url={"url": "file:///plugins", "dir_info": {"editable": True}},
    )
    _install(
        monkeypatch,
        [index_plugin, local_plugin, repository_plugin],
        {
            MODULES_ENTRY_POINT_GROUP: [
                _entry_point(
                    "example", index_plugin, modules=[ExampleModule, AnotherModule]
                ),
                _entry_point("local", local_plugin, modules=lambda: [ExampleModule]),
            ],
            IOS_CLI_PLUGIN_GROUP: [_entry_point("summarize", repository_plugin)],
            ANDROID_CLI_PLUGIN_GROUP: [_entry_point("triage", local_plugin)],
            NEUTRAL_CLI_PLUGIN_GROUP: [_entry_point("report", repository_plugin)],
        },
    )

    result = _run(plugins, ["list"])

    assert result.exit_code == 0
    # Plugins are listed by name, with the modules and the commands each of
    # them contributes.
    assert _table_header(result.output) == [
        "Name",
        "Version",
        "Origin",
        "Modules",
        "Commands",
    ]
    assert _table_rows(result.output) == [
        ["example-plugin", "1.2.0", "pypi", "2", "-"],
        ["local-plugin", "1.0.0", "local", "1", "triage"],
        ["repository-plugin", "0.1.0", "git+bbbbbbbb", "0", "report, summarize"],
    ]


def test_list_reports_a_broken_module_entry_point(monkeypatch):
    plugin = FakeDistribution("broken-plugin")
    _install(
        monkeypatch,
        [plugin],
        {
            MODULES_ENTRY_POINT_GROUP: [
                _entry_point(
                    "broken", plugin, exception=ImportError("missing dependency")
                )
            ]
        },
    )

    result = _run(plugins, ["list"])

    assert result.exit_code == 0
    assert _table_rows(result.output) == [
        ["broken-plugin", "1.0.0", "pypi", "error", "-"]
    ]


def test_list_without_plugins(monkeypatch):
    _install(monkeypatch, [], {})

    result = _run(plugins, ["list"])

    assert result.exit_code == 0
    assert result.output == "No MVT plugins are installed.\n"


def test_check_updates_prints_the_findings_and_ignores_the_throttle(monkeypatch):
    findings = [
        {
            "name": "example-plugin",
            "installed": "1.0.0",
            "latest": "1.2.0",
            "origin": "pypi",
            "upgrade_command": "pip install -U example-plugin",
        }
    ]
    _install(monkeypatch, [FakeDistribution("example-plugin")], {})
    monkeypatch.setattr(PluginUpdates, "check", lambda self: findings)
    monkeypatch.setattr(
        PluginUpdates,
        "should_check",
        lambda self: pytest.fail("an explicit check must not be throttled"),
    )

    result = _run(plugins, ["check-updates"])

    assert result.exit_code == 0
    assert "Plugin updates available:" in result.output
    assert "example-plugin  1.0.0 → 1.2.0" in result.output
    assert "Upgrade with: pip install -U example-plugin" in result.output
    assert "MVT does not install plugin updates." in result.output


def test_check_updates_without_available_updates(monkeypatch):
    _install(monkeypatch, [FakeDistribution("example-plugin")], {})
    monkeypatch.setattr(PluginUpdates, "check", lambda self: [])

    result = _run(plugins, ["check-updates"])

    assert result.exit_code == 0
    assert "All plugins are up to date." in result.output


def test_check_updates_without_plugins(monkeypatch):
    _install(monkeypatch, [], {})
    monkeypatch.setattr(
        PluginUpdates,
        "check",
        lambda self: pytest.fail("nothing must be checked without plugins"),
    )

    result = _run(plugins, ["check-updates"])

    assert result.exit_code == 0
    assert "No MVT plugins are installed." in result.output


def test_check_updates_without_network_access(monkeypatch):
    monkeypatch.setattr("mvt.common.cmd_plugins.settings.NETWORK_ACCESS_ALLOWED", False)
    monkeypatch.setattr(
        "mvt.common.cmd_plugins.installed_plugin_distributions",
        lambda: pytest.fail("plugins must not be listed without network access"),
    )
    monkeypatch.setattr(
        PluginUpdates,
        "check",
        lambda self: pytest.fail("nothing must be checked without network access"),
    )

    result = _run(plugins, ["check-updates"])

    assert result.exit_code == 0
    assert "Network access is disabled" in result.output
