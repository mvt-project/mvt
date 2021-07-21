# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 MVT Project Developers.
# See the file 'LICENSE' for usage and copying permissions, or find a copy at
#   https://github.com/mvt-project/mvt/blob/main/LICENSE

import os
import sys
import click
import argparse
import logging
from rich.logging import RichHandler

from mvt.common.module import run_module, save_timeline
from mvt.common.indicators import Indicators
from .download_apks import DownloadAPKs
from .lookups.koodous import koodous_lookup
from .lookups.virustotal import virustotal_lookup
from .modules.adb import ADB_MODULES
from .modules.backup import BACKUP_MODULES

# Setup logging using Rich.
LOG_FORMAT = "[%(name)s] %(message)s"
logging.basicConfig(level="INFO", format=LOG_FORMAT, handlers=[
    RichHandler(show_path=False, log_time_format="%X")])
log = logging.getLogger(__name__)

# Help messages of repeating options.
OUTPUT_HELP_MESSAGE = "Specify a path to a folder where you want to store JSON results"


#==============================================================================
# Main
#==============================================================================
@click.group(invoke_without_command=False)
def cli():
    return


#==============================================================================
# Download APKs
#==============================================================================
@cli.command("download-apks", help="Download all or non-safelisted installed APKs installed on the device")
@click.option("--all-apks", "-a", is_flag=True,
              help="Extract all packages installed on the phone, even those marked as safe")
@click.option("--virustotal", "-v", is_flag=True, help="Check packages on VirusTotal")
@click.option("--koodous", "-k", is_flag=True, help="Check packages on Koodous")
@click.option("--all-checks", "-A", is_flag=True, help="Run all available checks")
@click.option("--output", "-o", type=click.Path(exists=True),
              help="Specify a path to a folder where you want to store JSON results")
@click.option("--from-file", "-f", type=click.Path(exists=True),
              help="Instead of acquiring from phone, load an existing packages.json file for lookups (mainly for debug purposes)")
@click.option("--serial", "-s", type=str, help="Use the Android device with a given serial number")
def download_apks(all_apks, virustotal, koodous, all_checks, output, from_file, serial):
    try:
        if from_file:
            download = DownloadAPKs.from_json(from_file)
        else:
            if not output:
                log.critical("You need to specify an output folder (with --output, -o) when extracting APKs from a device")
                sys.exit(-1)

            download = DownloadAPKs(output_folder=output, all_apks=all_apks, serial=serial)
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
        sys.exit(-1)


#==============================================================================
# Checks through ADB
#==============================================================================
@cli.command("check-adb", help="Check an Android device over adb")
@click.option("--iocs", "-i", type=click.Path(exists=True), help="Path to indicators file")
@click.option("--output", "-o", type=click.Path(exists=True),
              help="Specify a path to a folder where you want to store JSON results")
@click.option("--list-modules", "-l", is_flag=True, help="Print list of available modules and exit")
@click.option("--module", "-m", help="Name of a single module you would like to run instead of all")
@click.option("--serial", "-s", type=str, help="Use the Android device with a given serial")
def check_adb(iocs, output, list_modules, module, serial):
    if list_modules:
        log.info("Following is the list of available check-adb modules:")
        for adb_module in ADB_MODULES:
            log.info(" - %s", adb_module.__name__)

        return

    log.info("Checking Android through adb bridge")

    if iocs:
        # Pre-load indicators for performance reasons.
        log.info("Loading indicators from provided file at %s", iocs)
        indicators = Indicators(iocs)

    timeline = []
    timeline_detected = []
    for adb_module in ADB_MODULES:
        if module and adb_module.__name__ != module:
            continue

        m = adb_module(output_folder=output, serial=serial, log=logging.getLogger(adb_module.__module__))

        if iocs:
            indicators.log = m.log
            m.indicators = indicators

        run_module(m)
        timeline.extend(m.timeline)
        timeline_detected.extend(m.timeline_detected)

    if output:
        if len(timeline) > 0:
            save_timeline(timeline, os.path.join(output, "timeline.csv"))
        if len(timeline_detected) > 0:
            save_timeline(timeline_detected, os.path.join(output, "timeline_detected.csv"))

#==============================================================================
# Check ADB backup
#==============================================================================
@cli.command("check-backup", help="Check an Android Backup")
@click.option("--iocs", "-i", type=click.Path(exists=True), help="Path to indicators file")
@click.option("--output", "-o", type=click.Path(exists=True), help=OUTPUT_HELP_MESSAGE)
@click.option("--serial", "-s", type=str, help="Use the Android device with a given serial")
@click.argument("BACKUP_PATH", type=click.Path(exists=True))
def check_backup(iocs, output, backup_path, serial):
    log.info("Checking ADB backup located at: %s", backup_path)

    if iocs:
        # Pre-load indicators for performance reasons.
        log.info("Loading indicators from provided file at %s", iocs)
        indicators = Indicators(iocs)

    if os.path.isfile(backup_path):
        log.critical("The path you specified is a not a folder!")

        if os.path.basename(backup_path) == "backup.ab":
            log.info("You can use ABE (https://github.com/nelenkov/android-backup-extractor) " \
                     "to extract 'backup.ab' files!")
        sys.exit(-1)

    for module in BACKUP_MODULES:
        m = module(base_folder=backup_path, output_folder=output,
                   serial=serial, log=logging.getLogger(module.__module__))

        if iocs:
            indicators.log = m.log
            m.indicators = indicators

        run_module(m)
