# Mobile Verification Toolkit (MVT) - Private
# Copyright (c) 2021-2023 Claudio Guarnieri.
# This file is part of MVT Private and its content is confidential.
# Please refer to the project maintainers before sharing with others.

import logging

from mvt.android.modules.androidqf.dumpsys_accessibility import \
    DumpsysAccessibility
from mvt.common.module import run_module

from ..utils import get_android_androidqf


class TestDumpsysAccessibilityModule:
    def test_parsing(self):
        data_path = get_android_androidqf()
        m = DumpsysAccessibility(target_path=data_path)
        run_module(m)
        assert len(m.results) == 4
        assert len(m.detected) == 0
