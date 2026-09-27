# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import shutil

from click.testing import CliRunner

from mvt.ios.cli import check_backup

from .utils import get_ios_backup_folder


class TestCheckBackupCommand:
    def test_check(self):
        runner = CliRunner()
        path = get_ios_backup_folder()
        result = runner.invoke(check_backup, [path])
        assert result.exit_code == 0

    def test_check_logs_the_backup_path_to_the_command_log(self, tmp_path):
        path = get_ios_backup_folder()
        output_path = tmp_path / "out"
        result = CliRunner().invoke(check_backup, ["--output", str(output_path), path])
        assert result.exit_code == 0
        command_log = (output_path / "command.log").read_text(encoding="utf-8")
        assert f"Checking iTunes backup located at: {path}" in command_log

    def test_check_finds_backup_in_subfolder(self, tmp_path, caplog):
        runner = CliRunner()
        backup_path = tmp_path / "MobileSync" / "Backup" / "device-id"
        shutil.copytree(get_ios_backup_folder(), backup_path)

        result = runner.invoke(check_backup, [str(backup_path.parent)])
        assert result.exit_code == 0
        assert f"Found iTunes backup in subfolder: {backup_path}" in caplog.text

    def test_check_rejects_non_backup_folder(self, tmp_path, caplog):
        runner = CliRunner()
        result = runner.invoke(check_backup, [str(tmp_path)])
        assert result.exit_code == 1
        assert "does not appear to be an iTunes backup folder" in caplog.text
