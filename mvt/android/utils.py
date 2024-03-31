# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
from datetime import datetime, timedelta
from typing import List


def warn_android_patch_level(patch_level: str, log) -> bool:
    """Alert if Android patch level out-of-date"""
    patch_date = datetime.strptime(patch_level, "%Y-%m-%d")
    if (datetime.now() - patch_date) > timedelta(days=6 * 31):
        log.warning(
            "This phone has not received security updates "
            "for more than six months (last update: %s)",
            patch_level,
        )
        return True

    return False


ROOT_PACKAGES: List[str] = [
    "com.noshufou.android.su",
    "com.noshufou.android.su.elite",
    "eu.chainfire.supersu",
    "com.koushikdutta.superuser",
    "com.thirdparty.superuser",
    "com.yellowes.su",
    "com.koushikdutta.rommanager",
    "com.koushikdutta.rommanager.license",
    "com.dimonvideo.luckypatcher",
    "com.chelpus.lackypatch",
    "com.ramdroid.appquarantine",
    "com.ramdroid.appquarantinepro",
    "com.devadvance.rootcloak",
    "com.devadvance.rootcloakplus",
    "de.robv.android.xposed.installer",
    "com.saurik.substrate",
    "com.zachspong.temprootremovejb",
    "com.amphoras.hidemyroot",
    "com.amphoras.hidemyrootadfree",
    "com.formyhm.hiderootPremium",
    "com.formyhm.hideroot",
    "me.phh.superuser",
    "eu.chainfire.supersu.pro",
    "com.kingouser.com",
    "com.topjohnwu.magisk",
]

DANGEROUS_PERMISSIONS_THRESHOLD = 10

DANGEROUS_PERMISSIONS = [
    "android.permission.ACCESS_COARSE_LOCATION",
    "android.permission.ACCESS_FINE_LOCATION",
    "android.permission.AUTHENTICATE_ACCOUNTS",
    "android.permission.CAMERA",
    "android.permission.DISABLE_KEYGUARD",
    "android.permission.PROCESS_OUTGOING_CALLS",
    "android.permission.READ_CALENDAR",
    "android.permission.READ_CALL_LOG",
    "android.permission.READ_CONTACTS",
    "android.permission.READ_PHONE_STATE",
    "android.permission.READ_SMS",
    "android.permission.RECEIVE_MMS",
    "android.permission.RECEIVE_SMS",
    "android.permission.RECEIVE_WAP_PUSH",
    "android.permission.RECORD_AUDIO",
    "android.permission.SEND_SMS",
    "android.permission.SYSTEM_ALERT_WINDOW",
    "android.permission.USE_CREDENTIALS",
    "android.permission.USE_SIP",
    "com.android.browser.permission.READ_HISTORY_BOOKMARKS",
]

SECURITY_PACKAGES = [
    "com.policydm",
    "com.samsung.android.app.omcagent",
    "com.samsung.android.securitylogagent",
    "com.sec.android.soagent",
]

SYSTEM_UPDATE_PACKAGES = [
    "com.android.updater",
    "com.google.android.gms",
    "com.huawei.android.hwouc",
    "com.lge.lgdmsclient",
    "com.motorola.ccc.ota",
    "com.oneplus.opbackup",
    "com.oppo.ota",
    "com.transsion.systemupdate",
    "com.wssyncmldm",
]
