# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import json
import logging

import pytest
from click.testing import CliRunner

from mvt.android.cli import cli as android_cli
from mvt.android.command_modules import ANDROID_CHECK_IOCS_MODULES
from mvt.common.cmd_check_iocs import CmdCheckIOCS
from mvt.common.module import MVTModule
from mvt.ios.cli import cli as ios_cli
from mvt.ios.command_modules import IOS_CHECK_IOCS_MODULES

# Keep the banner of the group callback from checking for updates online.
OFFLINE = ["--disable-update-check", "--disable-indicator-update-check"]


class CustomResultsModule(MVTModule):
    """A custom module which declares the check-iocs pair of both platforms."""

    slug = "custom_results"
    supported_commands = (
        ("ios", "check-backup"),
        ("ios", "check-iocs"),
        ("android", "check-iocs"),
    )

    checked: list = []

    def run(self) -> None:
        pass

    def check_indicators(self) -> None:
        self.checked.append(list(self.results))


class BackupOnlyModule(MVTModule):
    """A custom module which does not declare check-iocs."""

    slug = "backup_only"
    supported_commands = (("ios", "check-backup"),)

    def check_indicators(self) -> None:
        raise AssertionError("must not be re-checked")


@pytest.mark.parametrize(
    "platform, builtin_modules",
    [("ios", IOS_CHECK_IOCS_MODULES), ("android", ANDROID_CHECK_IOCS_MODULES)],
)
def test_check_iocs_rechecks_the_stored_results_of_custom_modules(
    platform, builtin_modules, tmp_path, caplog
):
    # check-iocs matches every <slug>.json in the results folder to the module
    # with that slug, custom modules included, and runs its check_indicators()
    # again over the stored results.
    results = [{"domain": "example.org"}]
    (tmp_path / "custom_results.json").write_text(json.dumps(results))
    (tmp_path / "backup_only.json").write_text(json.dumps(results))
    CustomResultsModule.checked.clear()

    cmd = CmdCheckIOCS(
        target_path=str(tmp_path),
        custom_modules=[CustomResultsModule, BackupOnlyModule],
        platform=platform,
    )
    cmd.modules = builtin_modules

    with caplog.at_level(logging.INFO):
        cmd.run()

    assert CustomResultsModule.checked == [results]
    assert (
        'Loading results from "custom_results.json" with module CustomResultsModule'
        in caplog.text
    )
    # A module declaring only check-backup is not part of check-iocs.
    assert "backup_only.json" not in caplog.text


def test_check_iocs_lists_custom_modules_declaring_the_command(caplog):
    cmd = CmdCheckIOCS(
        custom_modules=[CustomResultsModule, BackupOnlyModule],
        platform="ios",
    )
    cmd.modules = IOS_CHECK_IOCS_MODULES

    with caplog.at_level(logging.INFO):
        cmd.list_modules()

    assert "CustomResultsModule" in caplog.text
    assert "BackupOnlyModule" not in caplog.text


LOADED_MODULE = '''
from mvt.common.module import MVTModule


class LoadedResultsModule(MVTModule):
    """A module loaded from a file with --load-module."""

    slug = "loaded_results"
    supported_commands = (("ios", "check-iocs"), ("android", "check-iocs"))

    def run(self) -> None:
        pass

    def check_indicators(self) -> None:
        self.log.warning("loaded module checked %d results", len(self.results))
'''


@pytest.mark.parametrize("cli", [ios_cli, android_cli], ids=["mvt-ios", "mvt-android"])
def test_check_iocs_loads_custom_modules_from_a_file_on_each_cli(cli, tmp_path, caplog):
    module_path = tmp_path / "loaded_module.py"
    module_path.write_text(LOADED_MODULE)
    results_folder = tmp_path / "results"
    results_folder.mkdir()
    (results_folder / "loaded_results.json").write_text(json.dumps([{"a": 1}]))

    with caplog.at_level(logging.INFO):
        result = CliRunner().invoke(
            cli,
            [
                *OFFLINE,
                "check-iocs",
                "--load-module",
                str(module_path),
                str(results_folder),
            ],
        )

    assert result.exit_code == 0, result.output
    assert "loaded module checked 1 results" in caplog.text
