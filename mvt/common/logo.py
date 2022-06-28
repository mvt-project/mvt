# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from rich import print

from .updates import IndicatorsUpdates, MVTUpdates
from .version import MVT_VERSION


def check_updates() -> None:
    # First we check for MVT version udpates.
    mvt_updates = MVTUpdates()
    try:
        latest_version = mvt_updates.check()
    except Exception:
        pass
    else:
        if latest_version:
            print(f"\t\t[bold]Version {latest_version} is available! Upgrade mvt![/bold]")

    # Then we check for indicators files updates.
    ioc_updates = IndicatorsUpdates()

    # Before proceeding, we check if we have downloaded an indicators index.
    # If not, there's no point in proceeding with the updates check.
    if ioc_updates.get_latest_update() == 0:
        print("\t\t[bold]You have not yet downloaded any indicators, check the `download-iocs` command![/bold]")
        return

    # We only perform this check at a fixed frequency, in order to not
    # overburden the user with too many lookups if the command is being run
    # multiple times.
    should_check, hours = ioc_updates.should_check()
    if not should_check:
        print(f"\t\tIndicators updates checked recently, next automatic check in {int(hours)} hours")
        return

    try:
        ioc_to_update = ioc_updates.check()
    except Exception:
        pass
    else:
        if ioc_to_update:
            print("\t\t[bold]There are updates to your indicators files! Run the `download-iocs` command to update![/bold]")
        else:
            print("\t\tYour indicators files seem to be up to date.")


def logo() -> None:
    print("\n")
    print("\t[bold]MVT[/bold] - Mobile Verification Toolkit")
    print("\t\thttps://mvt.re")
    print(f"\t\tVersion: {MVT_VERSION}")

    check_updates()

    print("\n")
