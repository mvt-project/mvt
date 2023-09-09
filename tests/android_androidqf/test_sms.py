# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
from pathlib import Path

from mvt.android.modules.androidqf.sms import SMS
from mvt.common.module import run_module

from ..utils import get_android_androidqf, get_artifact_folder, list_files

TEST_BACKUP_PASSWORD = "123456"


class TestAndroidqfSMSAnalysis:
    def test_androidqf_sms(self):
        data_path = get_android_androidqf()
        m = SMS(target_path=data_path, log=logging)
        files = list_files(data_path)
        parent_path = Path(data_path).absolute().parent.as_posix()
        m.from_folder(parent_path, files)
        run_module(m)
        assert len(m.results) == 2
        assert len(m.timeline) == 0
        assert len(m.detected) == 0

    def test_androidqf_sms_encrypted_password_valid(self):
        data_path = os.path.join(get_artifact_folder(), "androidqf_encrypted")
        m = SMS(
            target_path=data_path,
            log=logging,
            module_options={"backup_password": TEST_BACKUP_PASSWORD},
        )
        files = list_files(data_path)
        parent_path = Path(data_path).absolute().parent.as_posix()
        m.from_folder(parent_path, files)
        run_module(m)
        assert len(m.results) == 1

    def test_androidqf_sms_encrypted_password_prompt(self, mocker):
        data_path = os.path.join(get_artifact_folder(), "androidqf_encrypted")
        prompt_mock = mocker.patch(
            "rich.prompt.Prompt.ask", return_value=TEST_BACKUP_PASSWORD
        )
        m = SMS(
            target_path=data_path,
            log=logging,
            module_options={},
        )
        files = list_files(data_path)
        parent_path = Path(data_path).absolute().parent.as_posix()
        m.from_folder(parent_path, files)
        run_module(m)
        assert prompt_mock.call_count == 1
        assert len(m.results) == 1

    def test_androidqf_sms_encrypted_password_invalid(self, caplog):
        data_path = os.path.join(get_artifact_folder(), "androidqf_encrypted")
        with caplog.at_level(logging.CRITICAL):
            m = SMS(
                target_path=data_path,
                log=logging,
                module_options={"backup_password": "invalid_password"},
            )
            files = list_files(data_path)
            parent_path = Path(data_path).absolute().parent.as_posix()
            m.from_folder(parent_path, files)
            run_module(m)
        assert len(m.results) == 0
        assert "Invalid backup password" in caplog.text

    def test_androidqf_sms_encrypted_no_interactive(self, caplog):
        data_path = os.path.join(get_artifact_folder(), "androidqf_encrypted")
        with caplog.at_level(logging.CRITICAL):
            m = SMS(
                target_path=data_path,
                log=logging,
                module_options={"interactive": False},
            )
            files = list_files(data_path)
            parent_path = Path(data_path).absolute().parent.as_posix()
            m.from_folder(parent_path, files)
            run_module(m)
        assert len(m.results) == 0
        assert (
            "Cannot decrypt backup because interactivity was disabled and the password was not supplied"
            in caplog.text
        )
