# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from .dumpsys_accessibility import DumpsysAccessibility
from .dumpsys_activities import DumpsysActivities
from .dumpsys_appops import DumpsysAppops
from .dumpsys_battery_daily import DumpsysBatteryDaily
from .dumpsys_battery_history import DumpsysBatteryHistory
from .dumpsys_dbinfo import DumpsysDBInfo
from .dumpsys_getprop import DumpsysGetProp
from .dumpsys_packages import DumpsysPackages
from .dumpsys_platform_compat import DumpsysPlatformCompat
from .dumpsys_receivers import DumpsysReceivers
from .dumpsys_adb_state import DumpsysADBState
from .fs_timestamps import BugReportTimestamps
from .tombstones import Tombstones

BUGREPORT_MODULES = [
    DumpsysAccessibility,
    DumpsysActivities,
    DumpsysAppops,
    DumpsysBatteryDaily,
    DumpsysBatteryHistory,
    DumpsysDBInfo,
    DumpsysGetProp,
    DumpsysPackages,
    DumpsysPlatformCompat,
    DumpsysReceivers,
    DumpsysADBState,
    BugReportTimestamps,
    Tombstones,
]
