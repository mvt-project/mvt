# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from .accessibility import Accessibility
from .activities import Activities
from .battery_daily import BatteryDaily
from .battery_history import BatteryHistory
from .dbinfo import DBInfo
from .packages import Packages
from .receivers import Receivers

BUGREPORT_MODULES = [Accessibility, Activities, BatteryDaily, BatteryHistory,
                     DBInfo, Packages, Receivers]
