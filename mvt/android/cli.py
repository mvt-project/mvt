# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import getpass
import io
import logging
import os
import tarfile
from pathlib import Path
from zipfile import ZipFile

import click
from rich.logging import RichHandler

from mvt.android.parsers.backup import (AndroidBackupParsingError,
                                        InvalidBackupPassword, parse_ab_header,
                                        parse_backup_file)
from mvt.common.help import (HELP_MSG_FAST, HELP_MSG_IOC,
                             HELP_MSG_LIST_MODULES, HELP_MSG_MODULE,
                             HELP_MSG_OUTPUT, HELP_MSG_SERIAL)
from mvt.common.indicators import Indicators, download_indicators_files
from mvt.common.logo import logo
from mvt.common.module import run_module, save_timeline

from .download_apks import DownloadAPKs
from .lookups.koodous import koodous_lookup
from .lookups.virustotal import virustotal_lookup
from .modules.adb import ADB_MODULES
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
@click.option("--koodous", "-k", is_flag=True, help="Check packages on Koodous")
@click.option("--all-checks", "-A", is_flag=True, help="Run all available checks")
@click.option("--output", "-o", type=click.Path(exists=False),
              help="Specify a path to a folder where you want to store the APKs")
@click.option("--from-file", "-f", type=click.Path(exists=True),
              help="Instead of acquiring from phone, load an existing packages.json file for lookups (mainly for debug purposes)")
@click.pass_context
def download_apks(ctx, all_apks, virustotal, koodous, all_checks, output, from_file, serial):
    try:
        if from_file:
            download = DownloadAPKs.from_json(from_file)
        else:
            # TODO: Do we actually want to be able to run without storing any file?
            if not output:
                log.critical("You need to specify an output folder with --output!")
                ctx.exit(1)

            if not os.path.exists(output):
                try:
                    os.makedirs(output)
                except Exception as e:
                    log.critical("Unable to create output folder %s: %s", output, e)
                    ctx.exit(1)

            download = DownloadAPKs(output_folder=output, all_apks=all_apks,
                                    log=logging.getLogger(DownloadAPKs.__module__))
            if serial:
                download.serial = serial
            download.run()

        packages = download.packages

        if len(packages) == 0:
            return

        if virustotal or all_checks:
            virustotal_lookup(packages)

        if koodous or all_checks:
            koodous_lookup(packages)
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
def check_adb(ctx, iocs, output, fast, list_modules, module, serial):
    if list_modules:
        log.info("Following is the list of available check-adb modules:")
        for adb_module in ADB_MODULES:
            log.info(" - %s", adb_module.__name__)

        return

    log.info("Checking Android through adb bridge")

    if output and not os.path.exists(output):
        try:
            os.makedirs(output)
        except Exception as e:
            log.critical("Unable to create output folder %s: %s", output, e)
            ctx.exit(1)

    indicators = Indicators(log=log)
    indicators.load_indicators_files(iocs)

    timeline = []
    timeline_detected = []
    for adb_module in ADB_MODULES:
        if module and adb_module.__name__ != module:
            continue

        m = adb_module(output_folder=output, fast_mode=fast,
                       log=logging.getLogger(adb_module.__module__))
        if indicators.total_ioc_count:
            m.indicators = indicators
            m.indicators.log = m.log
        if serial:
            m.serial = serial

        run_module(m)
        timeline.extend(m.timeline)
        timeline_detected.extend(m.timeline_detected)

    if output:
        if len(timeline) > 0:
            save_timeline(timeline, os.path.join(output, "timeline.csv"))
        if len(timeline_detected) > 0:
            save_timeline(timeline_detected, os.path.join(output, "timeline_detected.csv"))


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
    if list_modules:
        log.info("Following is the list of available check-bugreport modules:")
        for adb_module in BUGREPORT_MODULES:
            log.info(" - %s", adb_module.__name__)

        return

    log.info("Checking an Android Bug Report located at: %s", bugreport_path)

    if output and not os.path.exists(output):
        try:
            os.makedirs(output)
        except Exception as e:
            log.critical("Unable to create output folder %s: %s", output, e)
            ctx.exit(1)

    indicators = Indicators(log=log)
    indicators.load_indicators_files(iocs)

    if os.path.isfile(bugreport_path):
        bugreport_format = "zip"
        zip_archive = ZipFile(bugreport_path)
        zip_files = []
        for file_name in zip_archive.namelist():
            zip_files.append(file_name)
    elif os.path.isdir(bugreport_path):
        bugreport_format = "dir"
        folder_files = []
        parent_path = Path(bugreport_path).absolute().as_posix()
        for root, subdirs, subfiles in os.walk(os.path.abspath(bugreport_path)):
            for file_name in subfiles:
                folder_files.append(os.path.relpath(os.path.join(root, file_name), parent_path))

    timeline = []
    timeline_detected = []
    for bugreport_module in BUGREPORT_MODULES:
        if module and bugreport_module.__name__ != module:
            continue

        m = bugreport_module(base_folder=bugreport_path, output_folder=output,
                             log=logging.getLogger(bugreport_module.__module__))

        if bugreport_format == "zip":
            m.from_zip(zip_archive, zip_files)
        else:
            m.from_folder(bugreport_path, folder_files)

        if indicators.total_ioc_count:
            m.indicators = indicators
            m.indicators.log = m.log

        run_module(m)
        timeline.extend(m.timeline)
        timeline_detected.extend(m.timeline_detected)

    if output:
        if len(timeline) > 0:
            save_timeline(timeline, os.path.join(output, "timeline.csv"))
        if len(timeline_detected) > 0:
            save_timeline(timeline_detected, os.path.join(output, "timeline_detected.csv"))


#==============================================================================
# Command: check-backup
#==============================================================================
@cli.command("check-backup", help="Check an Android Backup")
@click.option("--serial", "-s", type=str, help=HELP_MSG_SERIAL)
@click.option("--iocs", "-i", type=click.Path(exists=True), multiple=True,
              default=[], help=HELP_MSG_IOC)
@click.option("--output", "-o", type=click.Path(exists=False), help=HELP_MSG_OUTPUT)
@click.argument("BACKUP_PATH", type=click.Path(exists=True))
@click.pass_context
def check_backup(ctx, iocs, output, backup_path, serial):
    log.info("Checking ADB backup located at: %s", backup_path)

    if os.path.isfile(backup_path):
        # AB File
        backup_type = "ab"
        with open(backup_path, "rb") as handle:
            data = handle.read()
        header = parse_ab_header(data)
        if not header["backup"]:
            log.critical("Invalid backup format, file should be in .ab format")
            ctx.exit(1)
        password = None
        if header["encryption"] != "none":
            password = getpass.getpass(prompt="Backup Password: ", stream=None)
        try:
            tardata = parse_backup_file(data, password=password)
        except InvalidBackupPassword:
            log.critical("Invalid backup password")
            ctx.exit(1)
        except AndroidBackupParsingError:
            log.critical("Impossible to parse this backup file, please use Android Backup Extractor instead")
            ctx.exit(1)

        dbytes = io.BytesIO(tardata)
        tar = tarfile.open(fileobj=dbytes)
        files = []
        for member in tar:
            files.append(member.name)

    elif os.path.isdir(backup_path):
        backup_type = "folder"
        backup_path = Path(backup_path).absolute().as_posix()
        files = []
        for root, subdirs, subfiles in os.walk(os.path.abspath(backup_path)):
            for fname in subfiles:
                files.append(os.path.relpath(os.path.join(root, fname), backup_path))
    else:
        log.critical("Invalid backup path, path should be a folder or an Android Backup (.ab) file")
        ctx.exit(1)

    if output and not os.path.exists(output):
        try:
            os.makedirs(output)
        except Exception as e:
            log.critical("Unable to create output folder %s: %s", output, e)
            ctx.exit(1)

    indicators = Indicators(log=log)
    indicators.load_indicators_files(iocs)

    for module in BACKUP_MODULES:
        m = module(base_folder=backup_path, output_folder=output,
                   log=logging.getLogger(module.__module__))
        if indicators.total_ioc_count:
            m.indicators = indicators
            m.indicators.log = m.log
        if serial:
            m.serial = serial

        if backup_type == "folder":
            m.from_folder(backup_path, files)
        else:
            m.from_ab(backup_path, tar, files)

        run_module(m)


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
    all_modules = []
    for entry in BACKUP_MODULES + ADB_MODULES:
        if entry not in all_modules:
            all_modules.append(entry)

    if list_modules:
        log.info("Following is the list of available check-iocs modules:")
        for iocs_module in all_modules:
            log.info(" - %s", iocs_module.__name__)

        return

    log.info("Checking stored results against provided indicators...")

    indicators = Indicators(log=log)
    indicators.load_indicators_files(iocs)

    total_detections = 0
    for file_name in os.listdir(folder):
        name_only, ext = os.path.splitext(file_name)
        file_path = os.path.join(folder, file_name)

        # TODO: Skipping processing of result files that are not json.
        #       We might want to revisit this eventually.
        if ext != ".json":
            continue

        for iocs_module in all_modules:
            if module and iocs_module.__name__ != module:
                continue

            if iocs_module().get_slug() != name_only:
                continue

            log.info("Loading results from \"%s\" with module %s", file_name,
                     iocs_module.__name__)

            m = iocs_module.from_json(file_path,
                                      log=logging.getLogger(iocs_module.__module__))
            if indicators.total_ioc_count > 0:
                m.indicators = indicators
                m.indicators.log = m.log

            try:
                m.check_indicators()
            except NotImplementedError:
                continue
            else:
                total_detections += len(m.detected)

    if total_detections > 0:
        log.warning("The check of the results produced %d detections!",
                    total_detections)


#==============================================================================
# Command: download-iocs
#==============================================================================
@cli.command("download-iocs", help="Download public STIX2 indicators")
def download_indicators():
    download_indicators_files(log)
