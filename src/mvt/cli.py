# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import click

from mvt.common.cli_plugins import (
    MVT_CUSTOM_COMMANDS_ENV,
    NEUTRAL_CLI_PLUGIN_GROUP,
    load_cli_commands_option,
    register_cli_plugins,
)
from mvt.common.completion import completion
from mvt.common.help import (
    HELP_MSG_DISABLE_INDICATOR_UPDATE_CHECK,
    HELP_MSG_DISABLE_UPDATE_CHECK,
    HELP_MSG_STIX2,
    HELP_MSG_VERSION,
)
from mvt.common.logo import logo
from mvt.common.updates import IndicatorsUpdates
from mvt.common.utils import init_logging

init_logging()

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


# ==============================================================================
# Main
# ==============================================================================
@click.group(invoke_without_command=True)
@load_cli_commands_option
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
    """Mobile Verification Toolkit.

    mvt-ios and mvt-android run the forensic analysis of an acquisition: each
    provides the check-* commands of its platform. This command hosts what
    belongs to neither platform; run it without a command to see the installed
    version and the list of what it offers.
    """
    ctx.ensure_object(dict)
    ctx.obj["disable_version_check"] = disable_update_check
    ctx.obj["disable_indicator_check"] = disable_indicator_update_check
    if ctx.invoked_subcommand != "completion":
        logo(
            disable_version_check=disable_update_check,
            disable_indicator_check=disable_indicator_update_check,
        )
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ==============================================================================
# Command: download-iocs
# ==============================================================================
@cli.command("download-iocs", context_settings=CONTEXT_SETTINGS, help=HELP_MSG_STIX2)
def download_iocs():
    ioc_updates = IndicatorsUpdates()
    ioc_updates.update()


# ==============================================================================
# Command: completion
# ==============================================================================
cli.add_command(completion)


# ==============================================================================
# Command: version
# ==============================================================================
@cli.command("version", context_settings=CONTEXT_SETTINGS, help=HELP_MSG_VERSION)
def version():
    return


# ==============================================================================
# Entry point of the mvt console script
# ==============================================================================
def main() -> None:
    """Register the external commands and run the mvt CLI.

    External commands are registered here rather than when this module is
    imported, so that importing MVT never runs third-party code and a plugin
    importing from MVT cannot re-enter a module that is still initializing.
    """
    register_cli_plugins(
        cli,
        entry_point_group=NEUTRAL_CLI_PLUGIN_GROUP,
        environment_variable=MVT_CUSTOM_COMMANDS_ENV,
    )
    cli()
