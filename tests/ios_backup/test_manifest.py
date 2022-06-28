# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

from mvt.common.indicators import Indicators
from mvt.common.module import run_module
from mvt.ios.modules.backup.manifest import Manifest

from ..utils import get_ios_backup_folder


class TestManifestModule:

    def test_manifest(self):
        m = Manifest(target_path=get_ios_backup_folder(), log=logging, results=[])
        run_module(m)
        assert len(m.results) == 3721
        assert len(m.timeline) == 5881
        assert len(m.detected) == 0

    def test_detection(self, indicator_file):
        m = Manifest(target_path=get_ios_backup_folder(), log=logging, results=[])
        ind = Indicators(log=logging)
        ind.parse_stix2(indicator_file)
        ind.ioc_collections[0]["file_names"].append("com.apple.CoreBrightness.plist")
        m.indicators = ind
        run_module(m)
        assert len(m.detected) == 1
