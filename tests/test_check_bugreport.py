# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import os

from click.testing import CliRunner

from mvt.android.cli import check_bugreport

from .utils import get_artifact_folder


class TestCheckBugreportCommand:

    def test_check(self):
        runner = CliRunner()
        path = os.path.join(get_artifact_folder(), "android_data/bugreport/")
        result = runner.invoke(check_bugreport, [path])
        assert result.exit_code == 0
