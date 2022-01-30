# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from .chrome_history import ChromeHistory
from .dumpsys_accessibility import DumpsysAccessibility
from .dumpsys_activities import DumpsysActivities
from .dumpsys_battery_history import DumpsysBatteryHistory
from .dumpsys_batterystats import DumpsysBatterystats
from .dumpsys_full import DumpsysFull
from .dumpsys_packages import DumpsysPackages
from .dumpsys_procstats import DumpsysProcstats
from .dumpsys_receivers import DumpsysReceivers
from .files import Files
from .getprop import Getprop
from .logcat import Logcat
from .packages import Packages
from .processes import Processes
from .root_binaries import RootBinaries
from .settings import Settings
from .sms import SMS
from .whatsapp import Whatsapp

ADB_MODULES = [ChromeHistory, SMS, Whatsapp, Processes, Getprop, Settings,
               DumpsysAccessibility, DumpsysBatterystats, DumpsysProcstats,
               DumpsysBatteryHistory, DumpsysPackages, DumpsysReceivers,
               DumpsysActivities, DumpsysFull, Packages, RootBinaries, Logcat,
               Files]
