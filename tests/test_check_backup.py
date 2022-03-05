# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from click.testing import CliRunner

from mvt.ios.cli import check_backup

from .utils import get_ios_backup_folder


class TestCheckBackupCommand:
    def test_check(self):
        runner = CliRunner()
        path = get_ios_backup_folder()
        result = runner.invoke(check_backup, [path])
        assert result.exit_code == 0
