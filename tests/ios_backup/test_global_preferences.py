# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from mvt.common.module import run_module
from mvt.common.alerts import AlertLevel
from mvt.ios.modules.mixed.global_preferences import GlobalPreferences

from ..utils import get_ios_backup_folder


class TestGlobalPreferencesModule:
    def test_global_preferences(self):
        m = GlobalPreferences(target_path=get_ios_backup_folder())
        run_module(m)
        assert len(m.results) == 16
        assert len(m.timeline) == 0
        assert len(m.alertstore.alerts) == 1

        lockdown_mode_alert = m.alertstore.alerts[0]
        assert lockdown_mode_alert.message == "Lockdown mode enabled"
        assert lockdown_mode_alert.level == AlertLevel.INFORMATIONAL

        assert m.results[0]["entry"] == "WebKitShowLinkPreviews"
        assert m.results[0]["value"] is False
