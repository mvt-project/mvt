import pytest
import logging

from mvt.ios.modules.mixed.tcc import TCC
from mvt.common.module import run_module

from ..utils import get_artifact_folder, init_setup

class TestManifestModule:
    @pytest.fixture(scope="session", autouse=True)
    def set(self):
        init_setup()

    def test_manifest(self):
        m = TCC(base_folder=get_artifact_folder(), log=logging)
        run_module(m)
        assert len(m.results) == 11
        # FIXME: TCC should suport timeline
        assert len(m.timeline) == 11
        assert len(m.detected) == 0
        assert m.results[0]["service"] == "kTCCServiceUbiquity"
        assert m.results[0]["auth_value"] == "allowed"
