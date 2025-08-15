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
from .dumpsys_packages import DumpsysPackages
from .dumpsys_receivers import DumpsysReceivers
from .dumpsys_adb import DumpsysADBState
from .getprop import Getprop
from .packages import Packages
from .dumpsys_platform_compat import DumpsysPlatformCompat
from .processes import Processes
from .settings import Settings
from .sms import SMS
from .files import Files
from .root_binaries import RootBinaries

ANDROIDQF_MODULES = [
    DumpsysActivities,
    DumpsysReceivers,
    DumpsysAccessibility,
    DumpsysAppops,
    DumpsysDBInfo,
    DumpsysBatteryDaily,
    DumpsysBatteryHistory,
    DumpsysADBState,
    Packages,
    DumpsysPlatformCompat,
    Processes,
    Getprop,
    Settings,
    SMS,
    DumpsysPackages,
    Files,
    RootBinaries,
]
