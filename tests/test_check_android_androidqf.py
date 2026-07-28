# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
import shutil
import tempfile
import zipfile

from click.testing import CliRunner

from mvt.android.cli import check_androidqf
from mvt.android.cmd_check_androidqf import CmdAndroidCheckAndroidQF
from mvt.android.modules.androidqf import ANDROIDQF_MODULES
from mvt.android.modules.androidqf.aqf_log_timestamps import AQFLogTimestamps
from mvt.common.config import settings

from .utils import get_artifact_folder

TEST_BACKUP_PASSWORD = "123456"


class TestCheckAndroidqfCommand:
    def test_log_timestamps_module_is_registered(self):
        assert AQFLogTimestamps in ANDROIDQF_MODULES

    def test_check(self):
        runner = CliRunner()
        path = os.path.join(get_artifact_folder(), "androidqf")
        result = runner.invoke(check_androidqf, [path])
        assert result.exit_code == 0

    def test_check_encrypted_backup_prompt_valid(self, mocker):
        """Prompt for password on CLI"""
        prompt_mock = mocker.patch(
            "mvt.android.modules.backup.helpers.prompt_password",
            return_value=TEST_BACKUP_PASSWORD,
        )

        runner = CliRunner()
        path = os.path.join(get_artifact_folder(), "androidqf_encrypted")
        result = runner.invoke(check_androidqf, [path])

        # The password entered for the AndroidQF SMS module is reused by the
        # nested backup command.
        assert prompt_mock.call_count == 1
        assert result.exit_code == 0

    def test_check_encrypted_backup_cli(self, mocker):
        """Provide password as CLI argument"""
        prompt_mock = mocker.patch(
            "mvt.android.modules.backup.helpers.prompt_password",
            return_value=TEST_BACKUP_PASSWORD,
        )

        runner = CliRunner()
        path = os.path.join(get_artifact_folder(), "androidqf_encrypted")
        result = runner.invoke(
            check_androidqf, ["--backup-password", TEST_BACKUP_PASSWORD, path]
        )

        assert prompt_mock.call_count == 0
        assert result.exit_code == 0

    def test_check_encrypted_backup_env(self, mocker):
        """Provide password as environment variable"""
        prompt_mock = mocker.patch(
            "mvt.android.modules.backup.helpers.prompt_password",
            return_value=TEST_BACKUP_PASSWORD,
        )

        os.environ["MVT_ANDROID_BACKUP_PASSWORD"] = TEST_BACKUP_PASSWORD
        settings.__init__()  # Reset settings

        runner = CliRunner()
        path = os.path.join(get_artifact_folder(), "androidqf_encrypted")
        result = runner.invoke(check_androidqf, [path])

        assert prompt_mock.call_count == 0
        assert result.exit_code == 0
        del os.environ["MVT_ANDROID_BACKUP_PASSWORD"]
        settings.__init__()  # Reset settings

    def test_check_malformed_backup_skips_backup_modules(self, tmp_path, caplog):
        path = tmp_path / "androidqf"
        shutil.copytree(os.path.join(get_artifact_folder(), "androidqf"), path)
        (path / "backup.ab").write_bytes(b"")

        runner = CliRunner()
        with caplog.at_level(logging.WARNING):
            result = runner.invoke(check_androidqf, [str(path)])

        assert result.exit_code == 0
        assert "Skipping backup modules as backup.ab is malformed" in caplog.text
        assert not any(
            record.levelname in {"CRITICAL", "FATAL"} for record in caplog.records
        )

    def test_intrusion_log_zip_rejects_path_traversal(self, tmp_path, mocker, caplog):
        escaped_name = f"mvt-escaped-{tmp_path.name}.txt"
        escaped_path = os.path.join(tempfile.gettempdir(), escaped_name)
        archive_path = tmp_path / "androidqf.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr(f"intrusion_logs/../{escaped_name}", "unsafe")
            archive.writestr("intrusion_logs/safe.txt", "safe")

        nested_command = mocker.patch(
            "mvt.android.cmd_check_androidqf.CmdAndroidCheckIntrusionLogs"
        )
        nested_command.return_value.timeline = []
        nested_command.return_value.alertstore.alerts = []
        command = CmdAndroidCheckAndroidQF(target_path=str(archive_path))
        command.init()

        with caplog.at_level(logging.WARNING):
            assert command.run_intrusion_logs_cmd() is True

        assert not os.path.exists(escaped_path)
        assert "Skipping unsafe intrusion log archive entry" in caplog.text
