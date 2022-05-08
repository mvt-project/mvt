# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from .accessibility import Accessibility
from .activities import Activities
from .appops import Appops
from .battery_daily import BatteryDaily
from .battery_history import BatteryHistory
from .dbinfo import DBInfo
from .getprop import Getprop
from .packages import Packages
from .receivers import Receivers

BUGREPORT_MODULES = [Accessibility, Activities, Appops, BatteryDaily,
                     BatteryHistory, DBInfo, Getprop, Packages, Receivers]
