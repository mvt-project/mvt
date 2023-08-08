# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

from mvt.common.indicators import Indicators
from mvt.common.module import run_module
from mvt.ios.modules.mixed.viber import Viber

from ..utils import get_ios_backup_folder


class TestViberModule:
    def test_viber(self):
        m = Viber(target_path=get_ios_backup_folder())
        run_module(m)
        assert len(m.results) == 2
        assert len(m.timeline) == 2
