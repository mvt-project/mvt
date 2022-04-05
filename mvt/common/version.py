# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import requests
from packaging import version

MVT_VERSION = "1.5.4"


def check_for_updates():
    res = requests.get("https://pypi.org/pypi/mvt/json")
    data = res.json()
    latest_version = data.get("info", {}).get("version", "")

    if version.parse(latest_version) > version.parse(MVT_VERSION):
        return latest_version

    return None
