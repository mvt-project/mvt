# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 MVT Project Developers.
# See the file 'LICENSE' for usage and copying permissions, or find a copy at
#   https://github.com/mvt-project/mvt/blob/main/LICENSE

import os
import sys
import click
import tarfile
import logging
from rich.logging import RichHandler

from mvt.common.module import run_module, save_timeline
from mvt.common.options import MutuallyExclusiveOption
from mvt.common.indicators import Indicators

from .decrypt import DecryptBackup
from .modules.fs import BACKUP_MODULES, FS_MODULES

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
# Command: decrypt-backup
#==============================================================================
@cli.command("decrypt-backup", help="Decrypt an encrypted iTunes backup")
@click.option("--destination", "-d", required=True,
              help="Path to the folder where to store the decrypted backup")
@click.option("--password", "-p", cls=MutuallyExclusiveOption,
              help="Password to use to decrypt the backup",
              prompt="Enter backup password", hide_input=True, prompt_required=False,
              mutually_exclusive=["key_file"])
@click.option("--key-file", "-k", cls=MutuallyExclusiveOption,
              type=click.Path(exists=True),
              help="File containing raw encryption key to use to decrypt the backup",
              mutually_exclusive=["password"])
@click.argument("BACKUP_PATH", type=click.Path(exists=True))
def decrypt_backup(destination, password, key_file, backup_path):
    backup = DecryptBackup(backup_path, destination)
    if password:
        backup.decrypt_with_password(password)
    elif key_file:
        backup.decrypt_with_key_file(key_file)
    else:
        raise click.ClickException("Missing required option. Specify either "
                                   "--password or --key-file.")


#==============================================================================
# Command: check-backup
#==============================================================================
@cli.command("check-backup", help="Extract artifacts from an iTunes backup")
@click.option("--iocs", "-i", type=click.Path(exists=True), help="Path to indicators file")
@click.option("--output", "-o", type=click.Path(exists=True), help=OUTPUT_HELP_MESSAGE)
@click.option("--fast", "-f", is_flag=True, help="Avoid running time/resource consuming features")
@click.option("--list-modules", "-l", is_flag=True, help="Print list of available modules and exit")
@click.option("--module", "-m", help="Name of a single module you would like to run instead of all")
@click.argument("BACKUP_PATH", type=click.Path(exists=True))
def check_backup(iocs, output, fast, backup_path, list_modules, module):
    if list_modules:
        log.info("Following is the list of available check-backup modules:")
        for backup_module in BACKUP_MODULES:
            log.info(" - %s", backup_module.__name__)

        return

    log.info("Checking iTunes backup located at: %s", backup_path)

    if iocs:
        # Pre-load indicators for performance reasons.
        log.info("Loading indicators from provided file at: %s", iocs)
        indicators = Indicators(iocs)

    timeline = []
    timeline_detected = []
    for backup_module in BACKUP_MODULES:
        if module and backup_module.__name__ != module:
            continue

        m = backup_module(base_folder=backup_path, output_folder=output, fast_mode=fast,
                          log=logging.getLogger(backup_module.__module__))
        m.is_backup = True

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
# Command: check-fs
#==============================================================================
@cli.command("check-fs", help="Extract artifacts from a full filesystem dump")
@click.option("--iocs", "-i", type=click.Path(exists=True), help="Path to indicators file")
@click.option("--output", "-o", type=click.Path(exists=True), help=OUTPUT_HELP_MESSAGE)
@click.option("--fast", "-f", is_flag=True, help="Avoid running time/resource consuming features")
@click.option("--list-modules", "-l", is_flag=True, help="Print list of available modules and exit")
@click.option("--module", "-m", help="Name of a single module you would like to run instead of all")
@click.argument("DUMP_PATH", type=click.Path(exists=True))
def check_fs(iocs, output, fast, dump_path, list_modules, module):
    if list_modules:
        log.info("Following is the list of available check-fs modules:")
        for fs_module in FS_MODULES:
            log.info(" - %s", fs_module.__name__)

        return

    log.info("Checking filesystem dump located at: %s", dump_path)

    if iocs:
        # Pre-load indicators for performance reasons.
        log.info("Loading indicators from provided file at: %s", iocs)
        indicators = Indicators(iocs)

    timeline = []
    timeline_detected = []
    for fs_module in FS_MODULES:
        if module and fs_module.__name__ != module:
            continue

        m = fs_module(base_folder=dump_path, output_folder=output, fast_mode=fast,
                      log=logging.getLogger(fs_module.__module__))

        m.is_fs_dump = True

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
# Command: check-iocs
#==============================================================================
@cli.command("check-iocs", help="Compare stored JSON results to provided indicators")
@click.option("--iocs", "-i", required=True, type=click.Path(exists=True),
              help="Path to indicators file")
@click.option("--list-modules", "-l", is_flag=True, help="Print list of available modules and exit")
@click.option("--module", "-m", help="Name of a single module you would like to run instead of all")
@click.argument("FOLDER", type=click.Path(exists=True))
def check_iocs(iocs, list_modules, module, folder):
    all_modules = []
    for entry in BACKUP_MODULES + FS_MODULES:
        if entry not in all_modules:
            all_modules.append(entry)

    if list_modules:
        log.info("Following is the list of available check-iocs modules:")
        for iocs_module in all_modules:
            log.info(" - %s", iocs_module.__name__)

        return

    log.info("Checking stored results against provided indicators...")

    # Pre-load indicators for performance reasons.
    log.info("Loading indicators from provided file at: %s", iocs)
    indicators = Indicators(iocs)

    for file_name in os.listdir(folder):
        name_only, ext = os.path.splitext(file_name)
        file_path = os.path.join(folder, file_name)

        for iocs_module in all_modules:
            if module and iocs_module.__name__ != module:
                continue

            if iocs_module().get_slug() != name_only:
                continue

            log.info("Loading results from \"%s\" with module %s", file_name,
                     iocs_module.__name__)

            m = iocs_module.from_json(file_path,
                                      log=logging.getLogger(iocs_module.__module__))

            indicators.log = m.log
            m.indicators = indicators

            try:
                m.check_indicators()
            except NotImplementedError:
                continue
