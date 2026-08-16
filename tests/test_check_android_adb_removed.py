# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from click.testing import CliRunner

from mvt.android.cli import check_adb


class TestCheckAndroidADBRemovedCommand:
    def test_check_adb_exits_nonzero(self):
        runner = CliRunner()
        result = runner.invoke(check_adb)

        assert result.exit_code == 1
