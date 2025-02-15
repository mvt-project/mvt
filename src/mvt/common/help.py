# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

# Help messages of generic options.
HELP_MSG_VERSION = "Show the currently installed version of MVT"
HELP_MSG_OUTPUT = "Specify a path to a folder where you want to store JSON results"
HELP_MSG_IOC = "Path to indicators file (can be invoked multiple time)"
HELP_MSG_FAST = "Avoid running time/resource consuming features"
HELP_MSG_LIST_MODULES = "Print list of available modules and exit"
HELP_MSG_MODULE = "Name of a single module you would like to run instead of all"
HELP_MSG_NONINTERACTIVE = "Don't ask interactive questions during processing"
HELP_MSG_HASHES = "Generate hashes of all the files analyzed"
HELP_MSG_VERBOSE = "Verbose mode"
HELP_MSG_CHECK_IOCS = "Compare stored JSON results to provided indicators"
HELP_MSG_STIX2 = "Download public STIX2 indicators"

# IOS Specific
HELP_MSG_DECRYPT_BACKUP = "Decrypt an encrypted iTunes backup"
HELP_MSG_BACKUP_DESTINATION = (
    "Path to the folder where the decrypted backup should be stored"
)
HELP_MSG_IOS_BACKUP_PASSWORD = (
    "Password to use to decrypt the backup (or, set the {MVT_IOS_BACKUP_PASSWORD} "
    "environment variable)"
)
HELP_MSG_BACKUP_KEYFILE = (
    "File containing raw encryption key to use to decrypt the backup"
)
HELP_MSG_EXTRACT_KEY = "Extract decryption key from an iTunes backup"
HELP_MSG_CHECK_IOS_BACKUP = "Extract artifacts from an iTunes backup"
HELP_MSG_CHECK_FS = "Extract artifacts from a full filesystem dump"

# Android Specific
HELP_MSG_ANDROID_BACKUP_PASSWORD = "The backup password to use for an Android backup"
HELP_MSG_CHECK_ADB_REMOVED = "REMOVED: Check an Android device over ADB"
HELP_MSG_CHECK_ADB_REMOVED_DESCRIPTION = (
    "The 'mvt-android check-adb' command has been removed from MVT. "
    "Use AndroidQF to collect full forensic artifacts from an Android device. \n\n"
    "The 'mvt-android check-androidqf' command in MVT can be used to fully analyze "
    "forensic data collected with AndroidQF. Minimal checks can also be performed "
    "on an Android bugreport using the 'mvt-android check-bugreport' command."
)
HELP_MSG_CHECK_BUGREPORT = "Check an Android Bug Report"
HELP_MSG_CHECK_ANDROID_BACKUP = "Check an Android Backup"
HELP_MSG_CHECK_ANDROIDQF = "Check data collected with AndroidQF"
