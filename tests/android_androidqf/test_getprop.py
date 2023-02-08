# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import os
import logging

from mvt.android.modules.androidqf.getprop import Getprop
from mvt.common.module import run_module

from ..utils import get_artifact_folder


class TestAndroidqfGetpropAnalysis:

    def test_androidqf_getprop(self):
        m = Getprop(target_path=os.path.join(get_artifact_folder(), "androidqf"), log=logging)
        run_module(m)
        assert len(m.results) == 10
        assert len(m.timeline) == 0
        assert len(m.detected) == 0
