# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from rich import print

from .version import MVT_VERSION, check_for_updates


def logo():
    print("\n")
    print("\t[bold]MVT[/bold] - Mobile Verification Toolkit")
    print("\t\thttps://mvt.re")
    print(f"\t\tVersion: {MVT_VERSION}")

    try:
        latest_version = check_for_updates()
    except Exception:
        pass
    else:
        if latest_version:
            print(f"\t\t[bold]Version {latest_version} is available! Upgrade mvt![/bold]")

    print("\n")
