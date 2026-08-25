# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

"""Module lists an mvt-android command composes from more than one family.

Commands whose modules are one family read that family directly. check-iocs
re-checks stored results, so it has to know every module that could have
written one, and both the CLI and any other code needing that answer share
the list from here rather than each concatenating their own.
"""

from mvt.common.module import MVTModule

from .modules.androidqf import ANDROIDQF_MODULES
from .modules.backup import BACKUP_MODULES
from .modules.bugreport import BUGREPORT_MODULES
from .modules.intrusion_logs import INTRUSION_LOGS_MODULES

ANDROID_CHECK_IOCS_MODULES: list[type[MVTModule]] = (
    BACKUP_MODULES + BUGREPORT_MODULES + ANDROIDQF_MODULES + INTRUSION_LOGS_MODULES
)
