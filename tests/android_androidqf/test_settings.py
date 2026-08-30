# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from pathlib import Path

from mvt.android.modules.androidqf.aqf_settings import AQFSettings
from mvt.android.artifacts.settings import Settings
from mvt.common.module import run_module

from ..utils import get_android_androidqf, list_files


class TestSettingsModule:
    def test_bugreport_settings_format(self):
        settings = Settings()
        settings.parse(
            "GLOBAL SETTINGS (user 0)\n"
            "_id:1 name:adb_wifi_enabled pkg:android value:0 default:0 defaultSystemSet:true\n"
            "SECURE SETTINGS (user 10)\n"
            "_id:2 name:accessibility_enabled pkg:android value:1\n"
        )

        assert settings.results == {
            "global:user_0": {"adb_wifi_enabled": "0"},
            "secure:user_10": {"accessibility_enabled": "1"},
        }

    def test_parsing(self):
        data_path = get_android_androidqf()
        m = AQFSettings(target_path=data_path)
        files = list_files(data_path)
        parent_path = Path(data_path).absolute().parent.as_posix()
        m.from_dir(parent_path, files)
        run_module(m)
        assert len(m.results) == 1
        assert "random" in m.results.keys()
        assert len(m.alertstore.alerts) == 1
        assert "samsung_errorlog_agree" in m.alertstore.alerts[0].message
