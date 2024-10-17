# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import os

from rich.prompt import Prompt

MVT_ANDROID_BACKUP_PASSWORD = "MVT_ANDROID_BACKUP_PASSWORD"


def cli_load_android_backup_password(log, backup_password):
    """
    Helper to load a backup password from CLI argument or environment variable

    Used in MVT CLI command parsers.
    """
    password_from_env = os.environ.get(MVT_ANDROID_BACKUP_PASSWORD, None)
    if backup_password:
        log.info(
            "Your password may be visible in the process table because it "
            "was supplied on the command line!"
        )
        if password_from_env:
            log.info(
                "Ignoring %s environment variable, using --backup-password argument instead",
                MVT_ANDROID_BACKUP_PASSWORD,
            )
        return backup_password
    elif password_from_env:
        log.info(
            "Using backup password from %s environment variable",
            MVT_ANDROID_BACKUP_PASSWORD,
        )
        return password_from_env


def prompt_or_load_android_backup_password(log, module_options):
    """
    Used in modules to either prompt or load backup password to use for encryption and decryption.
    """
    if module_options.get("backup_password", None):
        backup_password = module_options["backup_password"]
        log.info(
            "Using backup password passed from command line or environment variable."
        )

    # The default is to allow interactivity
    elif module_options.get("interactive", True):
        backup_password = Prompt.ask(prompt="Enter backup password", password=True)
    else:
        log.critical(
            "Cannot decrypt backup because interactivity"
            " was disabled and the password was not"
            " supplied"
        )
        return None

    return backup_password
