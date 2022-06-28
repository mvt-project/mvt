# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

from mvt.common.indicators import Indicators
from mvt.common.module import run_module
from mvt.ios.modules.mixed.tcc import TCC

from ..utils import get_ios_backup_folder


class TestTCCtModule:

    def test_tcc(self):
        m = TCC(target_path=get_ios_backup_folder(), log=logging, results=[])
        run_module(m)
        assert len(m.results) == 11
        assert len(m.timeline) == 11
        assert len(m.detected) == 0
        assert m.results[0]["service"] == "kTCCServiceUbiquity"
        assert m.results[0]["client"] == "com.apple.Preferences"
        assert m.results[0]["auth_value"] == "allowed"

    def test_tcc_detection(self, indicator_file):
        m = TCC(target_path=get_ios_backup_folder(), log=logging, results=[])
        ind = Indicators(log=logging)
        ind.parse_stix2(indicator_file)
        m.indicators = ind
        run_module(m)
        assert len(m.results) == 11
        assert len(m.timeline) == 11
        assert len(m.detected) == 1
        assert m.detected[0]["service"] == "kTCCServiceLiverpool"
        assert m.detected[0]["client"] == "Launch"
