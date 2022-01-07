import logging

from mvt.common.indicators import Indicators
from mvt.ios.modules.backup.manifest import Manifest
from mvt.common.module import run_module

from ..utils import get_backup_folder


class TestManifestModule:
    def test_manifest(self):
        m = Manifest(base_folder=get_backup_folder(), log=logging)
        run_module(m)
        assert len(m.results) == 3721
        assert len(m.timeline) == 5881
        assert len(m.detected) == 0

    def test_detection(self, indicator_file):
        m = Manifest(base_folder=get_backup_folder(), log=logging)
        ind = Indicators(log=logging)
        ind.parse_stix2(indicator_file)
        # Adds a file that exists in the manifest
        ind.ioc_files[0] = "com.apple.CoreBrightness.plist"
        m.indicators = ind
        run_module(m)
        assert len(m.detected) == 2
