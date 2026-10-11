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
from mvt.ios.modules.backup.manifest import Manifest

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


class BackupCheckerModule(MVTModule):
    """An iOS module which implements check_indicators() without declaring check-iocs."""

    slug = "backup_checker"
    supported_commands = (("ios", "check-backup"),)

    checked: list = []

    def run(self) -> None:
        pass

    def check_indicators(self) -> None:
        self.checked.append(list(self.results))


class BugReportCheckerModule(MVTModule):
    """The same for Android."""

    slug = "bugreport_checker"
    supported_commands = (("android", "check-bugreport"),)

    checked: list = []

    def run(self) -> None:
        pass

    def check_indicators(self) -> None:
        self.checked.append(list(self.results))


class BackupOnlyModule(MVTModule):
    """A custom module which does not implement check_indicators()."""

    slug = "backup_only"
    supported_commands = (("ios", "check-backup"),)

    def run(self) -> None:
        pass


@pytest.mark.parametrize(
    "platform, builtin_modules, checker_module",
    [
        ("ios", IOS_CHECK_IOCS_MODULES, BackupCheckerModule),
        ("android", ANDROID_CHECK_IOCS_MODULES, BugReportCheckerModule),
    ],
)
def test_check_iocs_rechecks_the_stored_results_of_custom_modules(
    platform, builtin_modules, checker_module, tmp_path, caplog
):
    # check-iocs matches every <slug>.json in the results folder to the module
    # with that slug, custom modules included, and runs its check_indicators()
    # again over the stored results.
    results = [{"domain": "example.org"}]
    (tmp_path / "custom_results.json").write_text(json.dumps(results))
    (tmp_path / f"{checker_module.slug}.json").write_text(json.dumps(results))
    (tmp_path / "backup_only.json").write_text(json.dumps(results))
    CustomResultsModule.checked.clear()
    checker_module.checked.clear()

    cmd = CmdCheckIOCS(
        target_path=str(tmp_path),
        custom_modules=[CustomResultsModule, checker_module, BackupOnlyModule],
        platform=platform,
    )
    cmd.modules = builtin_modules

    with caplog.at_level(logging.INFO):
        cmd.run()

    # A module which declares the check-iocs pair is re-checked.
    assert CustomResultsModule.checked == [results]
    assert (
        'Loading results from "custom_results.json" with module CustomResultsModule'
        in caplog.text
    )
    # So is a module which only implements check_indicators().
    assert checker_module.checked == [results]
    # A module which does neither is not part of check-iocs.
    assert "backup_only.json" not in caplog.text


@pytest.mark.parametrize(
    "platform, builtin_modules, listed, not_listed",
    [
        (
            "ios",
            IOS_CHECK_IOCS_MODULES,
            "BackupCheckerModule",
            "BugReportCheckerModule",
        ),
        (
            "android",
            ANDROID_CHECK_IOCS_MODULES,
            "BugReportCheckerModule",
            "BackupCheckerModule",
        ),
    ],
)
def test_check_iocs_lists_the_custom_modules_it_runs(
    platform, builtin_modules, listed, not_listed, caplog
):
    cmd = CmdCheckIOCS(
        custom_modules=[
            CustomResultsModule,
            BackupCheckerModule,
            BugReportCheckerModule,
            BackupOnlyModule,
        ],
        platform=platform,
    )
    cmd.modules = builtin_modules

    with caplog.at_level(logging.INFO):
        cmd.list_modules()

    assert "CustomResultsModule" in caplog.text
    # The module which implements check_indicators() for this platform is listed.
    assert listed in caplog.text
    # The one for the other platform is not, and neither is BackupOnlyModule.
    assert not_listed not in caplog.text
    assert "BackupOnlyModule" not in caplog.text


class ReplacementManifest(Manifest):
    """A replacement for a built-in module which does not declare check-iocs."""

    supported_commands = (("ios", "check-backup"),)
    replaces = Manifest


def test_check_iocs_uses_a_replacement_of_a_built_in_module():
    # A replacement which subclasses a built-in module inherits its
    # check_indicators(). check-iocs then runs it in place of that module.
    cmd = CmdCheckIOCS(custom_modules=[ReplacementManifest], platform="ios")
    cmd.modules = IOS_CHECK_IOCS_MODULES

    available = cmd._available_modules()

    assert ReplacementManifest in available
    assert Manifest not in available


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
