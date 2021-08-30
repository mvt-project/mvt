# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from .chrome_history import ChromeHistory
from .dumpsys_batterystats import DumpsysBatterystats
from .dumpsys_full import DumpsysFull
from .dumpsys_packages import DumpsysPackages
from .dumpsys_procstats import DumpsysProcstats
from .dumpsys_receivers import DumpsysReceivers
from .files import Files
from .logcat import Logcat
from .packages import Packages
from .processes import Processes
from .rootbinaries import RootBinaries
from .sms import SMS
from .whatsapp import Whatsapp

ADB_MODULES = [ChromeHistory, SMS, Whatsapp, Processes,
               DumpsysBatterystats, DumpsysProcstats,
               DumpsysPackages, DumpsysReceivers, DumpsysFull,
               Packages, RootBinaries, Logcat, Files]
