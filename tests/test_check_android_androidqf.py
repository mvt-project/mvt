# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import os

from click.testing import CliRunner

from mvt.android.cli import check_androidqf

from .utils import get_artifact_folder

TEST_BACKUP_PASSWORD = "123456"


class TestCheckAndroidqfCommand:
    def test_check(self):
        runner = CliRunner()
        path = os.path.join(get_artifact_folder(), "androidqf")
        result = runner.invoke(check_androidqf, [path])
        assert result.exit_code == 0

    def test_check_encrypted_backup_prompt_valid(self, mocker):
        """Prompt for password on CLI"""
        prompt_mock = mocker.patch(
            "rich.prompt.Prompt.ask", return_value=TEST_BACKUP_PASSWORD
        )

        runner = CliRunner()
        path = os.path.join(get_artifact_folder(), "androidqf_encrypted")
        result = runner.invoke(check_androidqf, [path])

        assert prompt_mock.call_count == 1
        assert result.exit_code == 0

    def test_check_encrypted_backup_cli(self, mocker):
        """Provide password as CLI argument"""
        prompt_mock = mocker.patch(
            "rich.prompt.Prompt.ask", return_value=TEST_BACKUP_PASSWORD
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
            "rich.prompt.Prompt.ask", return_value=TEST_BACKUP_PASSWORD
        )

        os.environ["MVT_ANDROID_BACKUP_PASSWORD"] = TEST_BACKUP_PASSWORD
        runner = CliRunner()
        path = os.path.join(get_artifact_folder(), "androidqf_encrypted")
        result = runner.invoke(check_androidqf, [path])

        assert prompt_mock.call_count == 0
        assert result.exit_code == 0
        del os.environ["MVT_ANDROID_BACKUP_PASSWORD"]
