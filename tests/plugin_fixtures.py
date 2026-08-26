# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

"""Helpers building throwaway plugin distributions for the tests.

Some plugin behaviour only shows up in a fresh interpreter: what an import
executes, and what a plugin sees when MVT is imported before or after it.
These helpers write an importable distribution with a real entry point and
run a script against it in a subprocess, with a temporary home so that the
subprocess cannot touch the configuration of whoever runs the tests.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

FIXTURE_COMMAND_NAME = "fixture-plugin"
FIXTURE_MODULE_NAME = "fixture_cli_plugin"
FIXTURE_DISTRIBUTION_NAME = "fixture-cli-plugin"


def write_cli_plugin_distribution(
    site_path: Path,
    entry_point_group: str,
    module_source: str,
) -> Path:
    """Write a distribution registering a CLI plugin entry point.

    :param site_path: Folder to write the distribution into, to be added to
                      the import path of the interpreter loading it.
    :param entry_point_group: Entry-point group to register the command in.
    :param module_source: Source of the plugin module, which must define a
                          Click command named `cli`.
    :returns: The folder the distribution was written to.
    """
    site_path.mkdir(parents=True, exist_ok=True)
    (site_path / f"{FIXTURE_MODULE_NAME}.py").write_text(
        module_source, encoding="utf-8"
    )

    dist_info = (
        site_path / f"{FIXTURE_DISTRIBUTION_NAME.replace('-', '_')}-1.0.dist-info"
    )
    dist_info.mkdir(exist_ok=True)
    (dist_info / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {FIXTURE_DISTRIBUTION_NAME}\nVersion: 1.0\n",
        encoding="utf-8",
    )
    (dist_info / "entry_points.txt").write_text(
        f"[{entry_point_group}]\n{FIXTURE_COMMAND_NAME} = {FIXTURE_MODULE_NAME}:cli\n",
        encoding="utf-8",
    )
    return site_path


def run_isolated_python(
    script: str,
    home: Path,
    site_path: Optional[Path] = None,
    **environment: str,
) -> subprocess.CompletedProcess:
    """Run a script in a fresh interpreter with its own configuration folder.

    Importing MVT writes its configuration file, so the subprocess gets a
    temporary home and no MVT environment variables from the test session.
    """
    isolated_environment = {
        key: value for key, value in os.environ.items() if not key.startswith("MVT_")
    }
    isolated_environment["HOME"] = str(home)
    isolated_environment["XDG_CONFIG_HOME"] = str(home / "config")
    isolated_environment["XDG_DATA_HOME"] = str(home / "data")
    if site_path is not None:
        isolated_environment["PYTHONPATH"] = str(site_path)
    isolated_environment.update(environment)

    return subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        env=isolated_environment,
    )
