# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from .dumpsys_accessibility import DumpsysAccessibility
from .dumpsys_activities import DumpsysActivities
from .dumpsys_appops import DumpsysAppops
from .dumpsys_packages import DumpsysPackages
from .dumpsys_receivers import DumpsysReceivers
from .getprop import Getprop
from .processes import Processes
from .settings import Settings
from .sms import SMS

ANDROIDQF_MODULES = [DumpsysActivities, DumpsysReceivers, DumpsysAccessibility,
                     DumpsysAppops, Processes, Getprop, Settings, SMS,
                     DumpsysPackages]
