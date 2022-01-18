# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

from mvt.common.module import run_module
from mvt.ios.modules.mixed.tcc import TCC

from ..utils import get_backup_folder


class TestManifestModule:
    def test_manifest(self):
        m = TCC(base_folder=get_backup_folder(), log=logging, results=[])
        run_module(m)
        assert len(m.results) == 11
        assert len(m.timeline) == 11
        assert len(m.detected) == 0
        assert m.results[0]["service"] == "kTCCServiceUbiquity"
        assert m.results[0]["auth_value"] == "allowed"

    def test_manifest_2(self):
        m = TCC(base_folder=get_backup_folder(), log=logging, results=[])
        run_module(m)
        assert len(m.results) == 11
        assert len(m.timeline) == 11
        assert len(m.detected) == 0
        assert m.results[0]["service"] == "kTCCServiceUbiquity"
        assert m.results[0]["auth_value"] == "allowed"
