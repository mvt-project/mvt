# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
import json
import pkgutil
from logging import Logger
from typing import Dict, Optional

import packaging

IPHONE_MODELS = json.loads(pkgutil.get_data("mvt", "ios/data/ios_models.json"))
IPHONE_IOS_VERSIONS = json.loads(pkgutil.get_data("mvt", "ios/data/ios_versions.json"))


def get_device_desc_from_id(identifier: str, devices_list: list = IPHONE_MODELS) -> str:
    for model in devices_list:
        if identifier == model["identifier"]:
            return model["description"]

    return ""


def find_version_by_build(build: str) -> str:
    build = build.upper()
    for version in IPHONE_IOS_VERSIONS:
        if build == version["build"]:
            return version["version"]

    return ""


def latest_ios_version() -> Dict[str, str]:
    return IPHONE_IOS_VERSIONS[-1]


def is_ios_version_outdated(version: str, log: Optional[Logger] = None) -> bool:
    """
    Check if the given version is below the latest version
    version can be a build number or version number
    Returns true if outdated for sure, false otherwise
    """
    # Check if it is a build
    if "." not in version:
        version = find_version_by_build(version)
        # If we can't find it
        if version == "":
            return False

    latest_parsed = packaging.version.parse(latest_ios_version()["version"])
    current_parsed = packaging.version.parse(version)
    if current_parsed < latest_parsed:
        if log:
            log.warning(
                "This phone is running an outdated iOS version: %s (latest is %s)",
                version,
                latest_ios_version()["version"],
            )
        return True
    return False
