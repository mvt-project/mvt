# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

import click

from mvt.common.cmd_check_iocs import CmdCheckIOCS
from mvt.common.help import (
    HELP_MSG_VERSION,
    HELP_MSG_OUTPUT,
    HELP_MSG_SERIAL,
    HELP_MSG_DOWNLOAD_APKS,
    HELP_MSG_DOWNLOAD_ALL_APKS,
    HELP_MSG_VIRUS_TOTAL,
    HELP_MSG_APK_OUTPUT,
    HELP_MSG_APKS_FROM_FILE,
    HELP_MSG_VERBOSE,
    HELP_MSG_CHECK_ADB,
    HELP_MSG_IOC,
    HELP_MSG_FAST,
    HELP_MSG_LIST_MODULES,
    HELP_MSG_MODULE,
    HELP_MSG_NONINTERACTIVE,
    HELP_MSG_ANDROID_BACKUP_PASSWORD,
    HELP_MSG_CHECK_BUGREPORT,
    HELP_MSG_CHECK_ANDROID_BACKUP,
    HELP_MSG_CHECK_ANDROIDQF,
    HELP_MSG_HASHES,
    HELP_MSG_CHECK_IOCS,
    HELP_MSG_STIX2,
    HELP_MSG_DELAY_CHECKS,
)
from mvt.common.logo import logo
from mvt.common.updates import IndicatorsUpdates
from mvt.common.utils import init_logging, set_verbose_logging

from .cmd_check_adb import CmdAndroidCheckADB
from .cmd_check_androidqf import CmdAndroidCheckAndroidQF
from .cmd_check_backup import CmdAndroidCheckBackup
from .cmd_check_bugreport import CmdAndroidCheckBugreport
from .cmd_download_apks import DownloadAPKs
from .modules.adb import ADB_MODULES
from .modules.adb.packages import Packages
from .modules.backup import BACKUP_MODULES
from .modules.backup.helpers import cli_load_android_backup_password
from .modules.bugreport import BUGREPORT_MODULES

init_logging()
log = logging.getLogger("mvt")

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


# ==============================================================================
# Main
# ==============================================================================
@click.group(invoke_without_command=False)
def cli():
    logo()


# ==============================================================================
# Command: version
# ==============================================================================
@cli.command("version", help=HELP_MSG_VERSION)
def version():
    return


# ==============================================================================
# Command: download-apks
# ==============================================================================
@cli.command(
    "download-apks", context_settings=CONTEXT_SETTINGS, help=HELP_MSG_DOWNLOAD_APKS
)
@click.option("--serial", "-s", type=str, help=HELP_MSG_SERIAL)
@click.option("--all-apks", "-a", is_flag=True, help=HELP_MSG_DOWNLOAD_ALL_APKS)
@click.option("--virustotal", "-V", is_flag=True, help=HELP_MSG_VIRUS_TOTAL)
@click.option("--delay", "-d", type=int, default=16, help=HELP_MSG_DELAY_CHECKS)
@click.option("--output", "-o", type=click.Path(exists=False), help=HELP_MSG_APK_OUTPUT)
@click.option(
    "--from-file", "-f", type=click.Path(exists=True), help=HELP_MSG_APKS_FROM_FILE
)
@click.option("--verbose", "-v", is_flag=True, help=HELP_MSG_VERBOSE)
@click.pass_context
def download_apks(ctx, all_apks, virustotal, output, from_file, serial, verbose, delay):
    set_verbose_logging(verbose)
    try:
        if from_file:
            download = DownloadAPKs.from_json(from_file)
        else:
            # TODO: Do we actually want to be able to run without storing any
            #       file?
            if not output:
                log.critical("You need to specify an output folder with --output!")
                ctx.exit(1)

            download = DownloadAPKs(results_path=output, all_apks=all_apks)
            if serial:
                download.serial = serial
            download.run()

        packages_to_lookup = []
        if all_apks:
            packages_to_lookup = download.packages
        else:
            for package in download.packages:
                if not package.get("system", False):
                    packages_to_lookup.append(package)

            if len(packages_to_lookup) == 0:
                return

        if virustotal:
            m = Packages()
            if delay:
                m.check_virustotal(packages_to_lookup, delay)
            else:
                delay = 0
                m.check_virustotal(packages_to_lookup, delay)
    except KeyboardInterrupt:
        print("")
        ctx.exit(1)


# ==============================================================================
# Command: check-adb
# ==============================================================================
@cli.command("check-adb", context_settings=CONTEXT_SETTINGS, help=HELP_MSG_CHECK_ADB)
@click.option("--serial", "-s", type=str, help=HELP_MSG_SERIAL)
@click.option(
    "--iocs",
    "-i",
    type=click.Path(exists=True),
    multiple=True,
    default=[],
    help=HELP_MSG_IOC,
)
@click.option("--output", "-o", type=click.Path(exists=False), help=HELP_MSG_OUTPUT)
@click.option("--fast", "-f", is_flag=True, help=HELP_MSG_FAST)
@click.option("--list-modules", "-l", is_flag=True, help=HELP_MSG_LIST_MODULES)
@click.option("--module", "-m", help=HELP_MSG_MODULE)
@click.option("--non-interactive", "-n", is_flag=True, help=HELP_MSG_NONINTERACTIVE)
@click.option("--backup-password", "-p", help=HELP_MSG_ANDROID_BACKUP_PASSWORD)
@click.option("--verbose", "-v", is_flag=True, help=HELP_MSG_VERBOSE)
@click.pass_context
def check_adb(
    ctx,
    serial,
    iocs,
    output,
    fast,
    list_modules,
    module,
    non_interactive,
    backup_password,
    verbose,
):
    set_verbose_logging(verbose)
    module_options = {
        "fast_mode": fast,
        "interactive": not non_interactive,
        "backup_password": cli_load_android_backup_password(log, backup_password),
    }

    cmd = CmdAndroidCheckADB(
        results_path=output,
        ioc_files=iocs,
        module_name=module,
        serial=serial,
        module_options=module_options,
    )

    if list_modules:
        cmd.list_modules()
        return

    log.info("Checking Android device over debug bridge")

    cmd.run()

    if cmd.detected_count > 0:
        log.warning(
            "The analysis of the Android device produced %d detections!",
            cmd.detected_count,
        )


# ==============================================================================
# Command: check-bugreport
# ==============================================================================
@cli.command(
    "check-bugreport", context_settings=CONTEXT_SETTINGS, help=HELP_MSG_CHECK_BUGREPORT
)
@click.option(
    "--iocs",
    "-i",
    type=click.Path(exists=True),
    multiple=True,
    default=[],
    help=HELP_MSG_IOC,
)
@click.option("--output", "-o", type=click.Path(exists=False), help=HELP_MSG_OUTPUT)
@click.option("--list-modules", "-l", is_flag=True, help=HELP_MSG_LIST_MODULES)
@click.option("--module", "-m", help=HELP_MSG_MODULE)
@click.option("--verbose", "-v", is_flag=True, help=HELP_MSG_VERBOSE)
@click.argument("BUGREPORT_PATH", type=click.Path(exists=True))
@click.pass_context
def check_bugreport(ctx, iocs, output, list_modules, module, verbose, bugreport_path):
    set_verbose_logging(verbose)
    # Always generate hashes as bug reports are small.
    cmd = CmdAndroidCheckBugreport(
        target_path=bugreport_path,
        results_path=output,
        ioc_files=iocs,
        module_name=module,
        hashes=True,
    )

    if list_modules:
        cmd.list_modules()
        return

    log.info("Checking Android bug report at path: %s", bugreport_path)

    cmd.run()

    if cmd.detected_count > 0:
        log.warning(
            "The analysis of the Android bug report produced %d detections!",
            cmd.detected_count,
        )


# ==============================================================================
# Command: check-backup
# ==============================================================================
@cli.command(
    "check-backup",
    context_settings=CONTEXT_SETTINGS,
    help=HELP_MSG_CHECK_ANDROID_BACKUP,
)
@click.option(
    "--iocs",
    "-i",
    type=click.Path(exists=True),
    multiple=True,
    default=[],
    help=HELP_MSG_IOC,
)
@click.option("--output", "-o", type=click.Path(exists=False), help=HELP_MSG_OUTPUT)
@click.option("--list-modules", "-l", is_flag=True, help=HELP_MSG_LIST_MODULES)
@click.option("--non-interactive", "-n", is_flag=True, help=HELP_MSG_NONINTERACTIVE)
@click.option("--backup-password", "-p", help=HELP_MSG_ANDROID_BACKUP_PASSWORD)
@click.option("--verbose", "-v", is_flag=True, help=HELP_MSG_VERBOSE)
@click.argument("BACKUP_PATH", type=click.Path(exists=True))
@click.pass_context
def check_backup(
    ctx,
    iocs,
    output,
    list_modules,
    non_interactive,
    backup_password,
    verbose,
    backup_path,
):
    set_verbose_logging(verbose)

    # Always generate hashes as backups are generally small.
    cmd = CmdAndroidCheckBackup(
        target_path=backup_path,
        results_path=output,
        ioc_files=iocs,
        hashes=True,
        module_options={
            "interactive": not non_interactive,
            "backup_password": cli_load_android_backup_password(log, backup_password),
        },
    )

    if list_modules:
        cmd.list_modules()
        return

    log.info("Checking Android backup at path: %s", backup_path)

    cmd.run()

    if cmd.detected_count > 0:
        log.warning(
            "The analysis of the Android backup produced %d detections!",
            cmd.detected_count,
        )


# ==============================================================================
# Command: check-androidqf
# ==============================================================================
@cli.command(
    "check-androidqf", context_settings=CONTEXT_SETTINGS, help=HELP_MSG_CHECK_ANDROIDQF
)
@click.option(
    "--iocs",
    "-i",
    type=click.Path(exists=True),
    multiple=True,
    default=[],
    help=HELP_MSG_IOC,
)
@click.option("--output", "-o", type=click.Path(exists=False), help=HELP_MSG_OUTPUT)
@click.option("--list-modules", "-l", is_flag=True, help=HELP_MSG_LIST_MODULES)
@click.option("--module", "-m", help=HELP_MSG_MODULE)
@click.option("--hashes", "-H", is_flag=True, help=HELP_MSG_HASHES)
@click.option("--non-interactive", "-n", is_flag=True, help=HELP_MSG_NONINTERACTIVE)
@click.option("--backup-password", "-p", help=HELP_MSG_ANDROID_BACKUP_PASSWORD)
@click.option("--verbose", "-v", is_flag=True, help=HELP_MSG_VERBOSE)
@click.argument("ANDROIDQF_PATH", type=click.Path(exists=True))
@click.pass_context
def check_androidqf(
    ctx,
    iocs,
    output,
    list_modules,
    module,
    hashes,
    non_interactive,
    backup_password,
    verbose,
    androidqf_path,
):
    set_verbose_logging(verbose)

    cmd = CmdAndroidCheckAndroidQF(
        target_path=androidqf_path,
        results_path=output,
        ioc_files=iocs,
        module_name=module,
        hashes=hashes,
        module_options={
            "interactive": not non_interactive,
            "backup_password": cli_load_android_backup_password(log, backup_password),
        },
    )

    if list_modules:
        cmd.list_modules()
        return

    log.info("Checking AndroidQF acquisition at path: %s", androidqf_path)

    cmd.run()

    if cmd.detected_count > 0:
        log.warning(
            "The analysis of the AndroidQF acquisition produced %d detections!",
            cmd.detected_count,
        )


# ==============================================================================
# Command: check-iocs
# ==============================================================================
@cli.command("check-iocs", context_settings=CONTEXT_SETTINGS, help=HELP_MSG_CHECK_IOCS)
@click.option(
    "--iocs",
    "-i",
    type=click.Path(exists=True),
    multiple=True,
    default=[],
    help=HELP_MSG_IOC,
)
@click.option("--list-modules", "-l", is_flag=True, help=HELP_MSG_LIST_MODULES)
@click.option("--module", "-m", help=HELP_MSG_MODULE)
@click.argument("FOLDER", type=click.Path(exists=True))
@click.pass_context
def check_iocs(ctx, iocs, list_modules, module, folder):
    cmd = CmdCheckIOCS(target_path=folder, ioc_files=iocs, module_name=module)
    cmd.modules = BACKUP_MODULES + ADB_MODULES + BUGREPORT_MODULES

    if list_modules:
        cmd.list_modules()
        return

    cmd.run()


# ==============================================================================
# Command: download-iocs
# ==============================================================================
@cli.command("download-iocs", context_settings=CONTEXT_SETTINGS, help=HELP_MSG_STIX2)
def download_indicators():
    ioc_updates = IndicatorsUpdates()
    ioc_updates.update()
