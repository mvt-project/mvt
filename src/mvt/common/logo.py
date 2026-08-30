# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

import requests
from rich import print as rich_print

from .config import settings
from .updates import (
    IndicatorsUpdates,
    MVTUpdates,
    PluginUpdates,
    installed_plugin_distributions,
)
from .version import MVT_VERSION


def _check_version_updates(log: logging.Logger) -> None:
    try:
        mvt_updates = MVTUpdates()
        latest_version = mvt_updates.check()
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        rich_print(
            "\t[bold]Note: Could not check for MVT updates.[/bold] "
            "You may be working offline. Please update MVT regularly."
        )
    except Exception as e:
        log.error("Error encountered when trying to check latest MVT version: %s", e)
    else:
        if latest_version:
            rich_print(
                f"\t[bold]Version {latest_version} is available! "
                "Upgrade mvt with `pip3 install -U mvt` or with `pipx upgrade mvt`[/bold]"
            )


def _check_indicator_updates(log: logging.Logger) -> None:
    ioc_updates = IndicatorsUpdates()

    # Before proceeding, we check if we have downloaded an indicators index.
    # If not, there's no point in proceeding with the updates check.
    if ioc_updates.get_latest_update() == 0:
        rich_print(
            "\t[bold]You have not yet downloaded any indicators, check "
            "the `download-iocs` command![/bold]"
        )
        return

    # We only perform this check at a fixed frequency, in order to not
    # overburden the user with too many lookups if the command is being run
    # multiple times.
    should_check, hours = ioc_updates.should_check()
    if not should_check:
        rich_print(
            f"\tIndicators updates checked recently, next automatic check "
            f"in {int(hours)} hours"
        )
        return

    try:
        ioc_to_update = ioc_updates.check()
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        rich_print(
            "\t[bold]Note: Could not check for indicator updates.[/bold] "
            "You may be working offline. Please update MVT indicators regularly."
        )
    except Exception as e:
        log.error("Error encountered when trying to check latest MVT indicators: %s", e)
    else:
        if ioc_to_update:
            rich_print(
                "\t[bold]There are updates to your indicators files! "
                "Run the `download-iocs` command to update![/bold]"
            )
        else:
            rich_print("\tYour indicators files seem to be up to date.")


def _print_plugin_updates(findings: list) -> None:
    if not findings:
        return

    rich_print("\t[bold]Plugin updates available:[/bold]")
    for finding in findings:
        rich_print(
            f"\t  {finding['name']}  {finding['installed']} → "
            f"{finding['latest']}   ({finding['upgrade_command']})"
        )


def _check_plugin_updates(log: logging.Logger) -> None:
    if not settings.NETWORK_ACCESS_ALLOWED:
        return

    # This runs on every command, so nothing here, including reading back what
    # the latest check stored, may ever interrupt MVT.
    try:
        distributions = installed_plugin_distributions()

        # There is nothing to check when MVT was not extended with any plugin.
        if not distributions:
            return

        plugin_updates = PluginUpdates()

        # We only perform this check at a fixed frequency, in order to not
        # overburden the user (and the plugin repositories) with too many
        # lookups. In between checks we print the findings of the latest one,
        # leaving out those which no longer apply to what is installed.
        should_check, _ = plugin_updates.should_check()
        if not should_check:
            _print_plugin_updates(plugin_updates.current_findings(distributions))
            return

        findings = plugin_updates.check()
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        rich_print(
            "\t[bold]Note: Could not check for plugin updates.[/bold] "
            "You may be working offline. Please update your MVT plugins regularly."
        )
    except Exception as e:
        log.error("Error encountered when trying to check MVT plugin updates: %s", e)
    else:
        _print_plugin_updates(findings)


def check_updates(
    disable_version_check: bool = False, disable_indicator_check: bool = False
) -> None:
    log = logging.getLogger("mvt")

    # First we check for MVT version updates.
    if not disable_version_check:
        _check_version_updates(log)

    # Then we check for indicators files updates.
    if not disable_indicator_check:
        _check_indicator_updates(log)

    # Finally we check for updates to the installed plugin packages. MVT never
    # installs an update itself, it only reports the command which does.
    if not disable_version_check:
        _check_plugin_updates(log)


def logo(
    disable_version_check: bool = False, disable_indicator_check: bool = False
) -> None:
    rich_print("\n")
    rich_print("\t[bold]MVT - Mobile Verification Toolkit[/bold]\n")
    rich_print("\thttps://mvt.re")
    rich_print(f"\tVersion: {MVT_VERSION}\n")

    check_updates(disable_version_check, disable_indicator_check)

    rich_print("\n")
