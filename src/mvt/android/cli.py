# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from zipfile import BadZipFile

import click

from mvt.common.cli_plugins import (
    ANDROID_CLI_PLUGIN_GROUP,
    MVT_ANDROID_CUSTOM_COMMANDS_ENV,
    load_cli_commands_option,
    register_cli_plugins,
)
from mvt.common.help import (
    HELP_MSG_ANDROID_BACKUP_PASSWORD,
    HELP_MSG_CHECK_ADB_REMOVED,
    HELP_MSG_CHECK_ADB_REMOVED_DESCRIPTION,
    HELP_MSG_CHECK_ANDROID_BACKUP,
    HELP_MSG_CHECK_ANDROIDQF,
    HELP_MSG_CHECK_BUGREPORT,
    HELP_MSG_CHECK_IOCS,
    HELP_MSG_CHECK_INTRUSION_LOGS,
    HELP_MSG_DELAY_CHECKS,
    HELP_MSG_DISABLE_INDICATOR_UPDATE_CHECK,
    HELP_MSG_DISABLE_UPDATE_CHECK,
    HELP_MSG_HASHES,
    HELP_MSG_IOC,
    HELP_MSG_LIST_MODULES,
    HELP_MSG_LOAD_MODULE,
    HELP_MSG_MODULE,
    HELP_MSG_NONINTERACTIVE,
    HELP_MSG_OUTPUT,
    HELP_MSG_STIX2,
    HELP_MSG_VERBOSE,
    HELP_MSG_VERBOSE_COMMAND,
    HELP_MSG_VERSION,
    HELP_MSG_VIRUS_TOTAL,
)
from mvt.common.utils import init_logging, set_verbose_logging

# The commands import what they run only when they are invoked. This module is
# imported at every start of mvt-android, including by shell completion on
# every keystroke, so importing it must do no more than build the command tree:
# the forensic modules, the backup parsers and the update checks stay out of it.

init_logging()
log = logging.getLogger("mvt")

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


def _get_disable_flags(ctx):
    """Helper function to safely get disable flags from context."""
    if ctx.obj is None:
        return False, False
    return (
        ctx.obj.get("disable_version_check", False),
        ctx.obj.get("disable_indicator_check", False),
    )


def _get_verbose(ctx):
    """Return whether --verbose was passed to the CLI itself."""
    return bool(ctx.obj and ctx.obj.get("verbose", False))


def _load_custom_modules(load_module):
    from mvt.common.module_loader import CustomModuleLoadError, load_custom_modules

    try:
        return load_custom_modules(load_module)
    except CustomModuleLoadError as exc:
        raise click.ClickException(str(exc)) from exc


# ==============================================================================
# Main
# ==============================================================================
@click.group(invoke_without_command=False)
@load_cli_commands_option
@click.option(
    "--disable-update-check", is_flag=True, help=HELP_MSG_DISABLE_UPDATE_CHECK
)
@click.option(
    "--disable-indicator-update-check",
    is_flag=True,
    help=HELP_MSG_DISABLE_INDICATOR_UPDATE_CHECK,
)
@click.option("--verbose", "-v", is_flag=True, help=HELP_MSG_VERBOSE)
@click.pass_context
def cli(ctx, disable_update_check, disable_indicator_update_check, verbose):
    ctx.ensure_object(dict)
    ctx.obj["disable_version_check"] = disable_update_check
    ctx.obj["disable_indicator_check"] = disable_indicator_update_check
    ctx.obj["verbose"] = verbose
    set_verbose_logging(verbose)

    from mvt.common.logo import logo

    logo(
        disable_version_check=disable_update_check,
        disable_indicator_check=disable_indicator_update_check,
    )


# ==============================================================================
# Command: version
# ==============================================================================
@cli.command("version", context_settings=CONTEXT_SETTINGS, help=HELP_MSG_VERSION)
def version():
    return


# ==============================================================================
# Command: check-adb (removed)
# ==============================================================================
@cli.command(
    "check-adb", context_settings=CONTEXT_SETTINGS, help=HELP_MSG_CHECK_ADB_REMOVED
)
@click.pass_context
def check_adb(ctx):
    log.error(HELP_MSG_CHECK_ADB_REMOVED_DESCRIPTION)
    ctx.exit(1)


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
@click.option(
    "--load-module",
    type=click.Path(exists=True),
    multiple=True,
    default=[],
    help=HELP_MSG_LOAD_MODULE,
)
@click.option("--verbose", "-v", is_flag=True, help=HELP_MSG_VERBOSE_COMMAND)
@click.argument("BUGREPORT_PATH", type=click.Path(exists=True))
@click.pass_context
def check_bugreport(
    ctx,
    iocs,
    output,
    list_modules,
    module,
    load_module,
    verbose,
    bugreport_path,
):
    from .cmd_check_bugreport import CmdAndroidCheckBugreport

    set_verbose_logging(verbose or _get_verbose(ctx))
    custom_modules = _load_custom_modules(load_module)
    # Always generate hashes as bug reports are small.
    cmd = CmdAndroidCheckBugreport(
        target_path=bugreport_path,
        results_path=output,
        ioc_files=iocs,
        module_name=module,
        hashes=True,
        disable_version_check=_get_disable_flags(ctx)[0],
        disable_indicator_check=_get_disable_flags(ctx)[1],
        custom_modules=custom_modules,
    )

    if list_modules:
        cmd.list_modules()
        return

    log.info("Checking Android bug report at path: %s", bugreport_path)

    try:
        cmd.run()
    except BadZipFile as exc:
        raise click.ClickException(f"Invalid bugreport archive: {exc}") from exc
    cmd.show_alerts_brief()
    cmd.show_support_message()


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
@click.option(
    "--load-module",
    type=click.Path(exists=True),
    multiple=True,
    default=[],
    help=HELP_MSG_LOAD_MODULE,
)
@click.option("--non-interactive", "-n", is_flag=True, help=HELP_MSG_NONINTERACTIVE)
@click.option("--backup-password", "-p", help=HELP_MSG_ANDROID_BACKUP_PASSWORD)
@click.option("--verbose", "-v", is_flag=True, help=HELP_MSG_VERBOSE_COMMAND)
@click.argument("BACKUP_PATH", type=click.Path(exists=True))
@click.pass_context
def check_backup(
    ctx,
    iocs,
    output,
    list_modules,
    load_module,
    non_interactive,
    backup_password,
    verbose,
    backup_path,
):
    from .cmd_check_backup import CmdAndroidCheckBackup
    from .modules.backup.helpers import cli_load_android_backup_password

    set_verbose_logging(verbose or _get_verbose(ctx))
    custom_modules = _load_custom_modules(load_module)

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
        disable_version_check=_get_disable_flags(ctx)[0],
        disable_indicator_check=_get_disable_flags(ctx)[1],
        custom_modules=custom_modules,
    )

    if list_modules:
        cmd.list_modules()
        return

    log.info("Checking Android backup at path: %s", backup_path)

    cmd.run()
    cmd.show_alerts_brief()
    cmd.show_support_message()


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
@click.option(
    "--load-module",
    type=click.Path(exists=True),
    multiple=True,
    default=[],
    help=HELP_MSG_LOAD_MODULE,
)
@click.option("--hashes", "-H", is_flag=True, help=HELP_MSG_HASHES)
@click.option("--virustotal", "-V", is_flag=True, help=HELP_MSG_VIRUS_TOTAL)
@click.option(
    "--delay", "-d", type=click.IntRange(min=0), default=16, help=HELP_MSG_DELAY_CHECKS
)
@click.option("--non-interactive", "-n", is_flag=True, help=HELP_MSG_NONINTERACTIVE)
@click.option("--backup-password", "-p", help=HELP_MSG_ANDROID_BACKUP_PASSWORD)
@click.option("--verbose", "-v", is_flag=True, help=HELP_MSG_VERBOSE_COMMAND)
@click.argument("ANDROIDQF_PATH", type=click.Path(exists=True))
@click.pass_context
def check_androidqf(
    ctx,
    iocs,
    output,
    list_modules,
    module,
    load_module,
    hashes,
    virustotal,
    delay,
    non_interactive,
    backup_password,
    verbose,
    androidqf_path,
):
    from .cmd_check_androidqf import CmdAndroidCheckAndroidQF
    from .modules.backup.helpers import cli_load_android_backup_password

    set_verbose_logging(verbose or _get_verbose(ctx))
    custom_modules = _load_custom_modules(load_module)

    cmd = CmdAndroidCheckAndroidQF(
        target_path=androidqf_path,
        results_path=output,
        ioc_files=iocs,
        module_name=module,
        hashes=hashes,
        module_options={
            "interactive": not non_interactive,
            "backup_password": cli_load_android_backup_password(log, backup_password),
            "virustotal": virustotal,
            "virustotal_delay": delay,
        },
        disable_version_check=_get_disable_flags(ctx)[0],
        disable_indicator_check=_get_disable_flags(ctx)[1],
        custom_modules=custom_modules,
    )

    if list_modules:
        cmd.list_modules()
        return

    log.info("Checking AndroidQF acquisition at path: %s", androidqf_path)

    cmd.run()
    cmd.show_alerts_brief()
    cmd.show_disable_adb_warning()
    cmd.show_support_message()


# ==============================================================================
# Command: check-intrusion-logs
# ==============================================================================
@cli.command(
    "check-intrusion-logs",
    context_settings=CONTEXT_SETTINGS,
    help=HELP_MSG_CHECK_INTRUSION_LOGS,
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
@click.option(
    "--load-module",
    type=click.Path(exists=True),
    multiple=True,
    default=[],
    help=HELP_MSG_LOAD_MODULE,
)
@click.option(
    "--timezone",
    "-t",
    default=None,
    help=(
        "IANA timezone name for the device, for example 'Europe/Paris'. "
        "When provided, event timestamps are expressed in the device's local "
        "time instead of UTC."
    ),
)
@click.option("--verbose", "-v", is_flag=True, help=HELP_MSG_VERBOSE_COMMAND)
@click.argument("LOGS_PATH", type=click.Path(exists=True))
@click.pass_context
def check_intrusion_logs(
    ctx,
    iocs,
    output,
    list_modules,
    module,
    load_module,
    timezone,
    verbose,
    logs_path,
):
    from .cmd_check_intrusion_logs import CmdAndroidCheckIntrusionLogs

    set_verbose_logging(verbose or _get_verbose(ctx))
    custom_modules = _load_custom_modules(load_module)

    module_options = {}
    if timezone:
        module_options["device_timezone"] = timezone

    cmd = CmdAndroidCheckIntrusionLogs(
        target_path=logs_path,
        results_path=output,
        ioc_files=iocs,
        module_name=module,
        module_options=module_options if module_options else None,
        disable_version_check=_get_disable_flags(ctx)[0],
        disable_indicator_check=_get_disable_flags(ctx)[1],
        custom_modules=custom_modules,
    )

    if list_modules:
        cmd.list_modules()
        return

    log.info("Checking intrusion logs at path: %s", logs_path)

    cmd.run()
    cmd.show_alerts_brief()
    cmd.show_support_message()


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
@click.option(
    "--load-module",
    type=click.Path(exists=True),
    multiple=True,
    default=[],
    help=HELP_MSG_LOAD_MODULE,
)
@click.argument("FOLDER", type=click.Path(exists=True))
@click.pass_context
def check_iocs(ctx, iocs, list_modules, module, load_module, folder):
    from mvt.common.cmd_check_iocs import CmdCheckIOCS

    from .command_modules import ANDROID_CHECK_IOCS_MODULES

    custom_modules = _load_custom_modules(load_module)
    cmd = CmdCheckIOCS(
        target_path=folder,
        ioc_files=iocs,
        module_name=module,
        disable_version_check=_get_disable_flags(ctx)[0],
        disable_indicator_check=_get_disable_flags(ctx)[1],
        custom_modules=custom_modules,
        platform="android",
    )
    cmd.modules = ANDROID_CHECK_IOCS_MODULES

    if list_modules:
        cmd.list_modules()
        return

    cmd.run()
    cmd.show_alerts_brief()
    cmd.show_support_message()


# ==============================================================================
# Command: download-iocs
# ==============================================================================
@cli.command("download-iocs", context_settings=CONTEXT_SETTINGS, help=HELP_MSG_STIX2)
def download_indicators():
    from mvt.common.updates import IndicatorsUpdates

    ioc_updates = IndicatorsUpdates()
    ioc_updates.update()


# ==============================================================================
# Entry point of the mvt-android console script
# ==============================================================================
def main() -> None:
    """Register the external commands and run the mvt-android CLI.

    External commands are registered here rather than when this module is
    imported, so that importing MVT never runs third-party code and a plugin
    importing from MVT cannot re-enter a module that is still initializing.
    """
    register_cli_plugins(
        cli,
        entry_point_group=ANDROID_CLI_PLUGIN_GROUP,
        environment_variable=MVT_ANDROID_CUSTOM_COMMANDS_ENV,
    )
    cli()
