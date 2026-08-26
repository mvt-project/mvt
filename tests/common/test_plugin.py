# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import mvt.plugin
from mvt.android.modules.backup.base import BackupModule
from mvt.common.config import settings

from ..plugin_fixtures import run_isolated_python


def test_the_exported_names_are_the_public_names():
    public = {name for name in vars(mvt.plugin) if not name.startswith("_")}

    assert public == set(mvt.plugin.__all__)
    assert mvt.plugin.settings is settings
    assert mvt.plugin.AndroidBackupModule is BackupModule


def test_the_surface_imports_before_anything_else_of_mvt(tmp_path):
    # A plugin can import the surface as its first import of MVT. The
    # subprocess gets a temporary home because importing MVT writes its
    # configuration file.
    result = run_isolated_python(
        "from mvt.plugin import IOSExtraction, MVT_VERSION, settings\n"
        "assert MVT_VERSION\n"
        "assert settings.NETWORK_TIMEOUT > 0\n"
        "assert IOSExtraction.__name__ == 'IOSExtraction'\n",
        home=tmp_path,
    )

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
