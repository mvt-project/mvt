# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from mvt.android.modules.androidqf.dumpsys_accessibility import DumpsysAccessibility
from mvt.common.module import run_module

from ..utils import get_android_androidqf


class TestDumpsysAccessibilityModule:
    def test_parsing(self):
        data_path = get_android_androidqf()
        m = DumpsysAccessibility(target_path=data_path)
        run_module(m)
        assert len(m.results) == 4
        assert len(m.detected) == 0
