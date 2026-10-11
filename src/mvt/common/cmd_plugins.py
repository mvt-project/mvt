# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import importlib.metadata
import logging
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from .cli_plugins import (
    ANDROID_CLI_PLUGIN_GROUP,
    IOS_CLI_PLUGIN_GROUP,
    NEUTRAL_CLI_PLUGIN_GROUP,
)
from .config import settings
from .help import (
    HELP_MSG_PLUGINS,
    HELP_MSG_PLUGINS_CHECK_UPDATES,
    HELP_MSG_PLUGINS_LIST,
)
from .module import MVTModule
from .module_loader import MODULES_ENTRY_POINT_GROUP, distribution_direct_url
from .updates import (
    SHORT_COMMIT_LENGTH,
    PluginUpdates,
    installed_plugin_distributions,
)

log = logging.getLogger(__name__)

CLI_PLUGIN_GROUPS = (
    IOS_CLI_PLUGIN_GROUP,
    ANDROID_CLI_PLUGIN_GROUP,
    NEUTRAL_CLI_PLUGIN_GROUP,
)
CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


def _entry_points(group: str) -> list[importlib.metadata.EntryPoint]:
    try:
        return list(importlib.metadata.entry_points(group=group))
    except Exception as exc:
        log.warning("Unable to discover the entry points in group %s: %s", group, exc)
        return []


def _entry_point_distribution(
    entry_point: importlib.metadata.EntryPoint,
) -> Optional[str]:
    dist = getattr(entry_point, "dist", None)
    if dist is None:
        return None
    try:
        return dist.name
    except Exception:
        return None


def _distribution_version(dist: importlib.metadata.Distribution) -> str:
    try:
        return dist.version or "unknown"
    except Exception:
        return "unknown"


def _distribution_origin(dist: importlib.metadata.Distribution) -> str:
    """Describe where a plugin package was installed from."""
    direct_url = distribution_direct_url(dist)
    if direct_url is None:
        return "pypi"

    vcs_info = direct_url.get("vcs_info")
    if isinstance(vcs_info, dict):
        commit = vcs_info.get("commit_id") or ""
        if commit:
            return f"git+{commit[:SHORT_COMMIT_LENGTH]}"
        return "git"

    return "local"


def _contributed_modules(
    entry_points: list[importlib.metadata.EntryPoint], distribution: str
) -> str:
    """Count the forensic modules a plugin package contributes.

    Entry points are resolved the way MVT resolves them when it loads
    modules, but a broken entry point is reported instead of raising: listing
    the installed plugins must work even when one of them is faulty.
    """
    count = 0
    broken = False

    for entry_point in entry_points:
        if _entry_point_distribution(entry_point) != distribution:
            continue
        try:
            loaded = entry_point.load()
            if callable(loaded) and not isinstance(loaded, type):
                loaded = loaded()
            count += sum(
                1
                for module in loaded
                if isinstance(module, type) and issubclass(module, MVTModule)
            )
        except (Exception, SystemExit) as exc:
            log.debug(
                "Unable to load the modules of entry point %s (%s): %s",
                entry_point.name,
                entry_point.value,
                exc,
            )
            broken = True

    if broken:
        return f"{count} (error)" if count else "error"

    return str(count)


def _contributed_commands(
    entry_points: list[importlib.metadata.EntryPoint], distribution: str
) -> str:
    names = {
        entry_point.name
        for entry_point in entry_points
        if _entry_point_distribution(entry_point) == distribution
    }

    return ", ".join(sorted(names)) if names else "-"


@click.group("plugins", context_settings=CONTEXT_SETTINGS, help=HELP_MSG_PLUGINS)
def plugins() -> None:
    pass


@plugins.command("list", context_settings=CONTEXT_SETTINGS, help=HELP_MSG_PLUGINS_LIST)
def list_plugins() -> None:
    distributions = installed_plugin_distributions()
    if not distributions:
        click.echo("No MVT plugins are installed.")
        return

    module_entry_points = _entry_points(MODULES_ENTRY_POINT_GROUP)
    command_entry_points = []
    for group in CLI_PLUGIN_GROUPS:
        command_entry_points.extend(_entry_points(group))

    table = Table(title="Installed MVT plugins")
    table.add_column("Name", style="bold")
    table.add_column("Version")
    table.add_column("Origin")
    table.add_column("Modules", justify="right")
    table.add_column("Commands")

    for dist in distributions:
        name = dist.name
        table.add_row(
            name,
            _distribution_version(dist),
            _distribution_origin(dist),
            _contributed_modules(module_entry_points, name),
            _contributed_commands(command_entry_points, name),
        )

    Console().print(table)


@plugins.command(
    "check-updates",
    context_settings=CONTEXT_SETTINGS,
    help=HELP_MSG_PLUGINS_CHECK_UPDATES,
    short_help="Check the installed plugins for updates",
)
def check_plugin_updates() -> None:
    if not settings.NETWORK_ACCESS_ALLOWED:
        click.echo(
            "Network access is disabled, cannot check for plugin updates. "
            "Enable NETWORK_ACCESS_ALLOWED in the MVT configuration to check."
        )
        return

    if not installed_plugin_distributions():
        click.echo("No MVT plugins are installed.")
        return

    findings = PluginUpdates().check()
    if not findings:
        click.echo("All plugins are up to date.")
        return

    click.echo("Plugin updates available:")
    for finding in findings:
        click.echo(f"  {finding['name']}  {finding['installed']} → {finding['latest']}")
        click.echo(f"    Upgrade with: {finding['upgrade_command']}")

    click.echo(
        "\nMVT does not install plugin updates. Run the command above when you "
        "decide to upgrade."
    )
