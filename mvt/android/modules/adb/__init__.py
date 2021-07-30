# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 MVT Project Developers.
# See the file 'LICENSE' for usage and copying permissions, or find a copy at
#   https://github.com/mvt-project/mvt/blob/main/LICENSE

from .chrome_history import ChromeHistory
from .dumpsys_batterystats import DumpsysBatterystats
from .dumpsys_packages import DumpsysPackages
from .dumpsys_procstats import DumpsysProcstats
from .packages import Packages
from .processes import Processes
from .rootbinaries import RootBinaries
from .sms import SMS
from .whatsapp import Whatsapp

ADB_MODULES = [ChromeHistory, SMS, Whatsapp, Processes,
               DumpsysBatterystats, DumpsysProcstats,
               DumpsysPackages, Packages, RootBinaries]
