# Mobile Verification Toolkit (MVT) - Private
# Copyright (c) 2021-2023 Claudio Guarnieri.
# This file is part of MVT Private and its content is confidential.
# Please refer to the project maintainers before sharing with others.

from mvt.common.module import run_module

from mvt.android.modules.androidqf.settings import Settings

from ..utils import get_android_androidqf


class TestSettingsModule:
    def test_parsing(self):
        data_path = get_android_androidqf()
        m = Settings(target_path=data_path)
        run_module(m)
        assert len(m.results) == 1
        assert "random" in m.results.keys()
        assert len(m.detected) == 0
