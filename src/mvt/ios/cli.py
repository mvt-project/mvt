# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import json
import logging
import os

import click
from rich.prompt import Prompt

from mvt.common.cmd_check_iocs import CmdCheckIOCS
from mvt.common.logo import logo
from mvt.common.options import MutuallyExclusiveOption
from mvt.common.updates import IndicatorsUpdates
from mvt.common.utils import (
    generate_hashes_from_path,
    init_logging,
    set_verbose_logging,
    CommandWrapperGroup,
)
from mvt.common.help import (
    HELP_MSG_VERSION,
    HELP_MSG_DECRYPT_BACKUP,
    HELP_MSG_BACKUP_DESTINATION,
    HELP_MSG_IOS_BACKUP_PASSWORD,
    HELP_MSG_BACKUP_KEYFILE,
    HELP_MSG_HASHES,
    HELP_MSG_EXTRACT_KEY,
    HELP_MSG_IOC,
    HELP_MSG_OUTPUT,
    HELP_MSG_FAST,
    HELP_MSG_LIST_MODULES,
    HELP_MSG_MODULE,
    HELP_MSG_VERBOSE,
    HELP_MSG_CHECK_FS,
    HELP_MSG_CHECK_IOCS,
    HELP_MSG_STIX2,
    HELP_MSG_CHECK_IOS_BACKUP,
    HELP_MSG_DISABLE_UPDATE_CHECK,
    HELP_MSG_DISABLE_INDICATOR_UPDATE_CHECK,
)
from .cmd_check_backup import CmdIOSCheckBackup
from .cmd_check_fs import CmdIOSCheckFS
from .decrypt import DecryptBackup
from .modules.backup import BACKUP_MODULES
from .modules.fs import FS_MODULES
from .modules.mixed import MIXED_MODULES

init_logging()
log = logging.getLogger("mvt")

# Set this environment variable to a password if needed.
MVT_IOS_BACKUP_PASSWORD = "MVT_IOS_BACKUP_PASSWORD"
CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


def _get_disable_flags(ctx):
    """Helper function to safely get disable flags from context."""
    if ctx.obj is None:
        return False, False
    return (
        ctx.obj.get("disable_version_check", False),
        ctx.obj.get("disable_indicator_check", False),
    )


# ==============================================================================
# Main
# ==============================================================================
@click.group(invoke_without_command=False, cls=CommandWrapperGroup)
@click.option(
    "--disable-update-check", is_flag=True, help=HELP_MSG_DISABLE_UPDATE_CHECK
)
@click.option(
    "--disable-indicator-update-check",
    is_flag=True,
    help=HELP_MSG_DISABLE_INDICATOR_UPDATE_CHECK,
)
@click.pass_context
def cli(ctx, disable_update_check, disable_indicator_update_check):
    ctx.ensure_object(dict)
    ctx.obj["disable_version_check"] = disable_update_check
    ctx.obj["disable_indicator_check"] = disable_indicator_update_check
    logo(
        disable_version_check=disable_update_check,
        disable_indicator_check=disable_indicator_update_check,
    )


# ==============================================================================
# Command: version
# ==============================================================================
@cli.command("version", help=HELP_MSG_VERSION)
def version():
    return


# ==============================================================================
# Command: decrypt-backup
# ==============================================================================
@cli.command(
    "decrypt-backup", context_settings=CONTEXT_SETTINGS, help=HELP_MSG_DECRYPT_BACKUP
)
@click.option("--destination", "-d", required=True, help=HELP_MSG_BACKUP_DESTINATION)
@click.option(
    "--password",
    "-p",
    cls=MutuallyExclusiveOption,
    mutually_exclusive=["key_file"],
    help=HELP_MSG_IOS_BACKUP_PASSWORD,
)
@click.option(
    "--key-file",
    "-k",
    cls=MutuallyExclusiveOption,
    type=click.Path(exists=True),
    mutually_exclusive=["password"],
    help=HELP_MSG_BACKUP_KEYFILE,
)
@click.option("--hashes", "-H", is_flag=True, help=HELP_MSG_HASHES)
@click.argument("BACKUP_PATH", type=click.Path(exists=True))
@click.pass_context
def decrypt_backup(ctx, destination, password, key_file, hashes, backup_path):
    backup = DecryptBackup(backup_path, destination)

    if key_file:
        if MVT_IOS_BACKUP_PASSWORD in os.environ:
            log.info(
                "Ignoring %s environment variable, using --key-file'%s' instead",
                MVT_IOS_BACKUP_PASSWORD,
                key_file,
            )

        backup.decrypt_with_key_file(key_file)
    elif password:
        log.info(
            "Your password may be visible in the process table because it "
            "was supplied on the command line!"
        )

        if MVT_IOS_BACKUP_PASSWORD in os.environ:
            log.info(
                "Ignoring %s environment variable, using --passwordargument instead",
                MVT_IOS_BACKUP_PASSWORD,
            )

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

    if hashes:
        info = {"encrypted": [], "decrypted": []}
        for file in generate_hashes_from_path(backup_path, log):
            info["encrypted"].append(file)
        for file in generate_hashes_from_path(destination, log):
            info["decrypted"].append(file)
        info_path = os.path.join(destination, "info.json")
        with open(info_path, "w+", encoding="utf-8") as handle:
            json.dump(info, handle, indent=4)


# ==============================================================================
# Command: extract-key
# ==============================================================================
@cli.command(
    "extract-key", context_settings=CONTEXT_SETTINGS, help=HELP_MSG_EXTRACT_KEY
)
@click.option("--password", "-p", help=HELP_MSG_IOS_BACKUP_PASSWORD)
@click.option(
    "--key-file",
    "-k",
    required=False,
    type=click.Path(exists=False, file_okay=True, dir_okay=False, writable=True),
    help=HELP_MSG_BACKUP_KEYFILE,
)
@click.argument("BACKUP_PATH", type=click.Path(exists=True))
def extract_key(password, key_file, backup_path):
    backup = DecryptBackup(backup_path)

    if password:
        log.info(
            "Your password may be visible in the process table because it "
            "was supplied on the command line!"
        )

        if MVT_IOS_BACKUP_PASSWORD in os.environ:
            log.info(
                "Ignoring %s environment variable, using --password argument instead",
                MVT_IOS_BACKUP_PASSWORD,
            )
    elif MVT_IOS_BACKUP_PASSWORD in os.environ:
        log.info("Using password from %s environment variable", MVT_IOS_BACKUP_PASSWORD)
        password = os.environ[MVT_IOS_BACKUP_PASSWORD]
    else:
        password = Prompt.ask("Enter backup password", password=True)

    backup.decrypt_with_password(password)
    backup.get_key()

    if key_file:
        backup.write_key(key_file)


# ==============================================================================
# Command: check-backup
# ==============================================================================
@cli.command(
    "check-backup", context_settings=CONTEXT_SETTINGS, help=HELP_MSG_CHECK_IOS_BACKUP
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
@click.option("--fast", "-f", is_flag=True, help=HELP_MSG_FAST)
@click.option("--list-modules", "-l", is_flag=True, help=HELP_MSG_LIST_MODULES)
@click.option("--module", "-m", help=HELP_MSG_MODULE)
@click.option("--hashes", "-H", is_flag=True, help=HELP_MSG_HASHES)
@click.option("--verbose", "-v", is_flag=True, help=HELP_MSG_VERBOSE)
@click.argument("BACKUP_PATH", type=click.Path(exists=True))
@click.pass_context
def check_backup(
    ctx, iocs, output, fast, list_modules, module, hashes, verbose, backup_path
):
    set_verbose_logging(verbose)
    module_options = {"fast_mode": fast}

    cmd = CmdIOSCheckBackup(
        target_path=backup_path,
        results_path=output,
        ioc_files=iocs,
        module_name=module,
        module_options=module_options,
        hashes=hashes,
        disable_version_check=_get_disable_flags(ctx)[0],
        disable_indicator_check=_get_disable_flags(ctx)[1],
    )

    if list_modules:
        cmd.list_modules()
        return

    log.info("Checking iTunes backup located at: %s", backup_path)

    cmd.run()

    if cmd.detected_count > 0:
        log.warning(
            "The analysis of the backup produced %d detections!", cmd.detected_count
        )


# ==============================================================================
# Command: check-fs
# ==============================================================================
@cli.command("check-fs", context_settings=CONTEXT_SETTINGS, help=HELP_MSG_CHECK_FS)
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
@click.option("--hashes", "-H", is_flag=True, help=HELP_MSG_HASHES)
@click.option("--verbose", "-v", is_flag=True, help=HELP_MSG_VERBOSE)
@click.argument("DUMP_PATH", type=click.Path(exists=True))
@click.pass_context
def check_fs(ctx, iocs, output, fast, list_modules, module, hashes, verbose, dump_path):
    set_verbose_logging(verbose)
    module_options = {"fast_mode": fast}

    cmd = CmdIOSCheckFS(
        target_path=dump_path,
        results_path=output,
        ioc_files=iocs,
        module_name=module,
        module_options=module_options,
        hashes=hashes,
        disable_version_check=_get_disable_flags(ctx)[0],
        disable_indicator_check=_get_disable_flags(ctx)[1],
    )

    if list_modules:
        cmd.list_modules()
        return

    log.info("Checking iOS filesystem located at: %s", dump_path)

    cmd.run()

    if cmd.detected_count > 0:
        log.warning(
            "The analysis of the iOS filesystem produced %d detections!",
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
    cmd = CmdCheckIOCS(
        target_path=folder,
        ioc_files=iocs,
        module_name=module,
        disable_version_check=_get_disable_flags(ctx)[0],
        disable_indicator_check=_get_disable_flags(ctx)[1],
    )
    cmd.modules = BACKUP_MODULES + FS_MODULES + MIXED_MODULES

    if list_modules:
        cmd.list_modules()
        return

    cmd.run()


# ==============================================================================
# Command: download-iocs
# ==============================================================================
@cli.command("download-iocs", context_settings=CONTEXT_SETTINGS, help=HELP_MSG_STIX2)
def download_iocs():
    ioc_updates = IndicatorsUpdates()
    ioc_updates.update()
