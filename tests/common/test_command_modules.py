# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from mvt.android.command_modules import ANDROID_CHECK_IOCS_MODULES
from mvt.android.modules.androidqf import ANDROIDQF_MODULES
from mvt.android.modules.backup import BACKUP_MODULES as ANDROID_BACKUP_MODULES
from mvt.android.modules.bugreport import BUGREPORT_MODULES
from mvt.android.modules.intrusion_logs import INTRUSION_LOGS_MODULES
from mvt.ios.command_modules import IOS_CHECK_IOCS_MODULES
from mvt.ios.modules.backup import BACKUP_MODULES as IOS_BACKUP_MODULES
from mvt.ios.modules.fs import FS_MODULES
from mvt.ios.modules.mixed import MIXED_MODULES


def test_the_check_iocs_lists_are_the_families_of_their_platform():
    # The CLI reads these same lists, so nothing composing one elsewhere can
    # drift from what the command runs. This pins what the lists are composed
    # of.
    assert IOS_CHECK_IOCS_MODULES == IOS_BACKUP_MODULES + FS_MODULES + MIXED_MODULES
    assert ANDROID_CHECK_IOCS_MODULES == (
        ANDROID_BACKUP_MODULES
        + BUGREPORT_MODULES
        + ANDROIDQF_MODULES
        + INTRUSION_LOGS_MODULES
    )
