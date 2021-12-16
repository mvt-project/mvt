import pytest
import logging
import os
from ..utils import get_artifact, get_artifact_folder, init_setup
from mvt.common.indicators import Indicators, IndicatorsFileBadFormat
from mvt.ios.modules.backup.manifest import Manifest
from mvt.common.module import run_module


class TestManifestModule:
    @pytest.fixture(scope="session", autouse=True)
    def set(self):
        init_setup()

    def test_manifest(self):
        m = Manifest(base_folder=get_artifact_folder(), log=logging)
        run_module(m)
        assert len(m.results) == 3721
        assert len(m.timeline) == 5881
        assert len(m.detected) == 0

    def test_detection(self):
        m = Manifest(base_folder=get_artifact_folder(), log=logging)
        ind = Indicators(log=logging)
        ind.parse_stix2(get_artifact("test.stix2"))
        # Adds a file that exists in the manifest
        ind.ioc_files[0] = "com.apple.CoreBrightness.plist"
        m.indicators = ind
        run_module(m)
        assert len(m.detected) == 2


