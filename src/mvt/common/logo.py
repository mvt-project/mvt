# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

import requests
from rich import print as rich_print

from .updates import IndicatorsUpdates, MVTUpdates
from .version import MVT_VERSION


def check_updates() -> None:
    log = logging.getLogger("mvt")
    # First we check for MVT version updates.
    try:
        mvt_updates = MVTUpdates()
        latest_version = mvt_updates.check()
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        rich_print(
            "\t\t[bold]Note: Could not check for MVT updates.[/bold] "
            "You may be working offline. Please update MVT regularly."
        )
    except Exception as e:
        log.error("Error encountered when trying to check latest MVT version: %s", e)
    else:
        if latest_version:
            rich_print(
                f"\t\t[bold]Version {latest_version} is available! "
                "Upgrade mvt with `pip3 install -U mvt`[/bold]"
            )

    # Then we check for indicators files updates.
    ioc_updates = IndicatorsUpdates()

    # Before proceeding, we check if we have downloaded an indicators index.
    # If not, there's no point in proceeding with the updates check.
    if ioc_updates.get_latest_update() == 0:
        rich_print(
            "\t\t[bold]You have not yet downloaded any indicators, check "
            "the `download-iocs` command![/bold]"
        )
        return

    # We only perform this check at a fixed frequency, in order to not
    # overburden the user with too many lookups if the command is being run
    # multiple times.
    should_check, hours = ioc_updates.should_check()
    if not should_check:
        rich_print(
            f"\t\tIndicators updates checked recently, next automatic check "
            f"in {int(hours)} hours"
        )
        return

    try:
        ioc_to_update = ioc_updates.check()
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        rich_print(
            "\t\t[bold]Note: Could not check for indicator updates.[/bold] "
            "You may be working offline. Please update MVT indicators regularly."
        )
    except Exception as e:
        log.error("Error encountered when trying to check latest MVT indicators: %s", e)
    else:
        if ioc_to_update:
            rich_print(
                "\t\t[bold]There are updates to your indicators files! "
                "Run the `download-iocs` command to update![/bold]"
            )
        else:
            rich_print("\t\tYour indicators files seem to be up to date.")


def logo() -> None:
    rich_print("\n")
    rich_print("\t[bold]MVT[/bold] - Mobile Verification Toolkit")
    rich_print("\t\thttps://mvt.re")
    rich_print(f"\t\tVersion: {MVT_VERSION}")

    check_updates()

    rich_print("\n")
