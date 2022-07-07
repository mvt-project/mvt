# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

import click
from rich.logging import RichHandler

from mvt.common.cmd_check_iocs import CmdCheckIOCS
from mvt.common.help import (HELP_MSG_FAST, HELP_MSG_IOC,
                             HELP_MSG_LIST_MODULES, HELP_MSG_MODULE,
                             HELP_MSG_OUTPUT, HELP_MSG_SERIAL)
from mvt.common.logo import logo
from mvt.common.updates import IndicatorsUpdates

from .cmd_check_adb import CmdAndroidCheckADB
from .cmd_check_backup import CmdAndroidCheckBackup
from .cmd_check_bugreport import CmdAndroidCheckBugreport
from .cmd_download_apks import DownloadAPKs
from .modules.adb import ADB_MODULES
from .modules.adb.packages import Packages
from .modules.backup import BACKUP_MODULES
from .modules.bugreport import BUGREPORT_MODULES

# Setup logging using Rich.
LOG_FORMAT = "[%(name)s] %(message)s"
logging.basicConfig(level="INFO", format=LOG_FORMAT, handlers=[
    RichHandler(show_path=False, log_time_format="%X")])
log = logging.getLogger(__name__)


#==============================================================================
# Main
#==============================================================================
@click.group(invoke_without_command=False)
def cli():
    logo()


#==============================================================================
# Command: version
#==============================================================================
@cli.command("version", help="Show the currently installed version of MVT")
def version():
    return


#==============================================================================
# Command: download-apks
#==============================================================================
@cli.command("download-apks", help="Download all or only non-system installed APKs")
@click.option("--serial", "-s", type=str, help=HELP_MSG_SERIAL)
@click.option("--all-apks", "-a", is_flag=True,
              help="Extract all packages installed on the phone, including system packages")
@click.option("--virustotal", "-v", is_flag=True, help="Check packages on VirusTotal")
@click.option("--output", "-o", type=click.Path(exists=False),
              help="Specify a path to a folder where you want to store the APKs")
@click.option("--from-file", "-f", type=click.Path(exists=True),
              help="Instead of acquiring from phone, load an existing packages.json file for lookups (mainly for debug purposes)")
@click.pass_context
def download_apks(ctx, all_apks, virustotal, output, from_file, serial):
    try:
        if from_file:
            download = DownloadAPKs.from_json(from_file)
        else:
            # TODO: Do we actually want to be able to run without storing any file?
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
            m.check_virustotal(packages_to_lookup)
    except KeyboardInterrupt:
        print("")
        ctx.exit(1)


#==============================================================================
# Command: check-adb
#==============================================================================
@cli.command("check-adb", help="Check an Android device over adb")
@click.option("--serial", "-s", type=str, help=HELP_MSG_SERIAL)
@click.option("--iocs", "-i", type=click.Path(exists=True), multiple=True,
              default=[], help=HELP_MSG_IOC)
@click.option("--output", "-o", type=click.Path(exists=False),
              help=HELP_MSG_OUTPUT)
@click.option("--fast", "-f", is_flag=True, help=HELP_MSG_FAST)
@click.option("--list-modules", "-l", is_flag=True, help=HELP_MSG_LIST_MODULES)
@click.option("--module", "-m", help=HELP_MSG_MODULE)
@click.pass_context
def check_adb(ctx, serial, iocs, output, fast, list_modules, module):
    cmd = CmdAndroidCheckADB(results_path=output, ioc_files=iocs,
                             module_name=module, serial=serial, fast_mode=fast)

    if list_modules:
        cmd.list_modules()
        return

    log.info("Checking Android device over debug bridge")

    cmd.run()

    if len(cmd.timeline_detected) > 0:
        log.warning("The analysis of the Android device produced %d detections!",
                    len(cmd.timeline_detected))


#==============================================================================
# Command: check-bugreport
#==============================================================================
@cli.command("check-bugreport", help="Check an Android Bug Report")
@click.option("--iocs", "-i", type=click.Path(exists=True), multiple=True,
              default=[], help=HELP_MSG_IOC)
@click.option("--output", "-o", type=click.Path(exists=False), help=HELP_MSG_OUTPUT)
@click.option("--list-modules", "-l", is_flag=True, help=HELP_MSG_LIST_MODULES)
@click.option("--module", "-m", help=HELP_MSG_MODULE)
@click.argument("BUGREPORT_PATH", type=click.Path(exists=True))
@click.pass_context
def check_bugreport(ctx, iocs, output, list_modules, module, bugreport_path):
    cmd = CmdAndroidCheckBugreport(target_path=bugreport_path, results_path=output,
                                   ioc_files=iocs, module_name=module)

    if list_modules:
        cmd.list_modules()
        return

    log.info("Checking Android bug report at path: %s", bugreport_path)

    cmd.run()

    if len(cmd.timeline_detected) > 0:
        log.warning("The analysis of the Android bug report produced %d detections!",
                    len(cmd.timeline_detected))


#==============================================================================
# Command: check-backup
#==============================================================================
@cli.command("check-backup", help="Check an Android Backup")
@click.option("--serial", "-s", type=str, help=HELP_MSG_SERIAL)
@click.option("--iocs", "-i", type=click.Path(exists=True), multiple=True,
              default=[], help=HELP_MSG_IOC)
@click.option("--output", "-o", type=click.Path(exists=False), help=HELP_MSG_OUTPUT)
@click.option("--list-modules", "-l", is_flag=True, help=HELP_MSG_LIST_MODULES)
@click.argument("BACKUP_PATH", type=click.Path(exists=True))
@click.pass_context
def check_backup(ctx, serial, iocs, output, list_modules, backup_path):
    cmd = CmdAndroidCheckBackup(target_path=backup_path, results_path=output,
                                ioc_files=iocs)

    if list_modules:
        cmd.list_modules()
        return

    log.info("Checking Android backup at path: %s", backup_path)

    cmd.run()

    if len(cmd.timeline_detected) > 0:
        log.warning("The analysis of the Android backup produced %d detections!",
                    len(cmd.timeline_detected))


#==============================================================================
# Command: check-iocs
#==============================================================================
@cli.command("check-iocs", help="Compare stored JSON results to provided indicators")
@click.option("--iocs", "-i", type=click.Path(exists=True), multiple=True,
              default=[], help=HELP_MSG_IOC)
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


#==============================================================================
# Command: download-iocs
#==============================================================================
@cli.command("download-iocs", help="Download public STIX2 indicators")
def download_indicators():
    ioc_updates = IndicatorsUpdates()
    ioc_updates.update()
