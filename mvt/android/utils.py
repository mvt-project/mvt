# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
from datetime import datetime, timedelta


def warn_android_patch_level(patch_level: str, log) -> bool:
    """Alert if Android patch level out-of-date"""
    patch_date = datetime.strptime(patch_level, "%Y-%m-%d")
    if (datetime.now() - patch_date) > timedelta(days=6 * 31):
        log.warning(
            "This phone has not received security updates "
            "for more than six months (last update: %s)",
            patch_level,
        )
        return True

    return False
