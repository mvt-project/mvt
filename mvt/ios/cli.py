# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os

import click
from rich.logging import RichHandler
from rich.prompt import Prompt

from mvt.common.cmd_check_iocs import CmdCheckIOCS
from mvt.common.help import (HELP_MSG_FAST, HELP_MSG_IOC,
                             HELP_MSG_LIST_MODULES, HELP_MSG_MODULE,
                             HELP_MSG_OUTPUT)
from mvt.common.logo import logo
from mvt.common.options import MutuallyExclusiveOption
from mvt.common.updates import IndicatorsUpdates

from .cmd_check_backup import CmdIOSCheckBackup
from .cmd_check_fs import CmdIOSCheckFS
from .decrypt import DecryptBackup
from .modules.backup import BACKUP_MODULES
from .modules.fs import FS_MODULES
from .modules.mixed import MIXED_MODULES

# Setup logging using Rich.
LOG_FORMAT = "[%(name)s] %(message)s"
logging.basicConfig(level="INFO", format=LOG_FORMAT, handlers=[
    RichHandler(show_path=False, log_time_format="%X")])
log = logging.getLogger(__name__)

# Set this environment variable to a password if needed.
MVT_IOS_BACKUP_PASSWORD = "MVT_IOS_BACKUP_PASSWORD"


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
# Command: decrypt-backup
#==============================================================================
@cli.command("decrypt-backup", help="Decrypt an encrypted iTunes backup")
@click.option("--destination", "-d", required=True,
              help="Path to the folder where to store the decrypted backup")
@click.option("--password", "-p", cls=MutuallyExclusiveOption,
              help=f"Password to use to decrypt the backup (or, set {MVT_IOS_BACKUP_PASSWORD} environment variable)",
              mutually_exclusive=["key_file"])
@click.option("--key-file", "-k", cls=MutuallyExclusiveOption,
              type=click.Path(exists=True),
              help="File containing raw encryption key to use to decrypt the backup",
              mutually_exclusive=["password"])
@click.argument("BACKUP_PATH", type=click.Path(exists=True))
@click.pass_context
def decrypt_backup(ctx, destination, password, key_file, backup_path):
    backup = DecryptBackup(backup_path, destination)

    if key_file:
        if MVT_IOS_BACKUP_PASSWORD in os.environ:
            log.info("Ignoring environment variable, using --key-file '%s' instead",
                     MVT_IOS_BACKUP_PASSWORD, key_file)

        backup.decrypt_with_key_file(key_file)
    elif password:
        log.info("Your password may be visible in the process table because it was supplied on the command line!")

        if MVT_IOS_BACKUP_PASSWORD in os.environ:
            log.info("Ignoring %s environment variable, using --password argument instead",
                     MVT_IOS_BACKUP_PASSWORD)

        backup.decrypt_with_password(password)
    elif MVT_IOS_BACKUP_PASSWORD in os.environ:
        log.info("Using password from %s environment variable", MVT_IOS_BACKUP_PASSWORD)
        backup.decrypt_with_password(os.environ[MVT_IOS_BACKUP_PASSWORD])
    else:
        sekrit = Prompt.ask("Enter backup password", password=True)
        backup.decrypt_with_password(sekrit)

    if not backup.can_process():
        ctx.exit(1)

    backup.process_backup()


#==============================================================================
# Command: extract-key
#==============================================================================
@cli.command("extract-key", help="Extract decryption key from an iTunes backup")
@click.option("--password", "-p",
              help=f"Password to use to decrypt the backup (or, set {MVT_IOS_BACKUP_PASSWORD} environment variable)")
@click.option("--key-file", "-k",
              help="Key file to be written (if unset, will print to STDOUT)",
              required=False,
              type=click.Path(exists=False, file_okay=True, dir_okay=False, writable=True))
@click.argument("BACKUP_PATH", type=click.Path(exists=True))
def extract_key(password, key_file, backup_path):
    backup = DecryptBackup(backup_path)

    if password:
        log.info("Your password may be visible in the process table because it was supplied on the command line!")

        if MVT_IOS_BACKUP_PASSWORD in os.environ:
            log.info("Ignoring %s environment variable, using --password argument instead",
                     MVT_IOS_BACKUP_PASSWORD)
    elif MVT_IOS_BACKUP_PASSWORD in os.environ:
        log.info("Using password from %s environment variable", MVT_IOS_BACKUP_PASSWORD)
        password = os.environ[MVT_IOS_BACKUP_PASSWORD]
    else:
        password = Prompt.ask("Enter backup password", password=True)

    backup.decrypt_with_password(password)
    backup.get_key()

    if key_file:
        backup.write_key(key_file)


#==============================================================================
# Command: check-backup
#==============================================================================
@cli.command("check-backup", help="Extract artifacts from an iTunes backup")
@click.option("--iocs", "-i", type=click.Path(exists=True), multiple=True,
              default=[], help=HELP_MSG_IOC)
@click.option("--output", "-o", type=click.Path(exists=False), help=HELP_MSG_OUTPUT)
@click.option("--fast", "-f", is_flag=True, help=HELP_MSG_FAST)
@click.option("--list-modules", "-l", is_flag=True, help=HELP_MSG_LIST_MODULES)
@click.option("--module", "-m", help=HELP_MSG_MODULE)
@click.argument("BACKUP_PATH", type=click.Path(exists=True))
@click.pass_context
def check_backup(ctx, iocs, output, fast, list_modules, module, backup_path):
    cmd = CmdIOSCheckBackup(target_path=backup_path, results_path=output,
                            ioc_files=iocs, module_name=module, fast_mode=fast)

    if list_modules:
        cmd.list_modules()
        return

    log.info("Checking iTunes backup located at: %s", backup_path)

    cmd.run()

    if len(cmd.timeline_detected) > 0:
        log.warning("The analysis of the backup produced %d detections!",
                    len(cmd.timeline_detected))


#==============================================================================
# Command: check-fs
#==============================================================================
@cli.command("check-fs", help="Extract artifacts from a full filesystem dump")
@click.option("--iocs", "-i", type=click.Path(exists=True), multiple=True,
              default=[], help=HELP_MSG_IOC)
@click.option("--output", "-o", type=click.Path(exists=False), help=HELP_MSG_OUTPUT)
@click.option("--fast", "-f", is_flag=True, help=HELP_MSG_FAST)
@click.option("--list-modules", "-l", is_flag=True, help=HELP_MSG_LIST_MODULES)
@click.option("--module", "-m", help=HELP_MSG_MODULE)
@click.argument("DUMP_PATH", type=click.Path(exists=True))
@click.pass_context
def check_fs(ctx, iocs, output, fast, list_modules, module, dump_path):
    cmd = CmdIOSCheckFS(target_path=dump_path, results_path=output,
                        ioc_files=iocs, module_name=module, fast_mode=fast)

    if list_modules:
        cmd.list_modules()
        return

    log.info("Checking iOS filesystem located at: %s", dump_path)

    cmd.run()

    if len(cmd.timeline_detected) > 0:
        log.warning("The analysis of the iOS filesystem produced %d detections!",
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
    cmd.modules = BACKUP_MODULES + FS_MODULES + MIXED_MODULES

    if list_modules:
        cmd.list_modules()
        return

    cmd.run()


#==============================================================================
# Command: download-iocs
#==============================================================================
@cli.command("download-iocs", help="Download public STIX2 indicators")
def download_iocs():
    ioc_updates = IndicatorsUpdates()
    ioc_updates.update()
