# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from .chrome_history import ChromeHistory
from .dumpsys_full import DumpsysFull
from .files import Files
from .getprop import Getprop
from .logcat import Logcat
from .packages import Packages
from .processes import Processes
from .root_binaries import RootBinaries
from .selinux_status import SELinuxStatus
from .settings import Settings
from .sms import SMS
from .whatsapp import Whatsapp

ADB_MODULES = [
    ChromeHistory,
    SMS,
    Whatsapp,
    Processes,
    Getprop,
    Settings,
    SELinuxStatus,
    DumpsysFull,
    Packages,
    Logcat,
    RootBinaries,
    Files,
]
