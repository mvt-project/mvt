import pytest
import logging
import os
from ..utils import get_artifact, get_artifact_folder, init_setup
from mvt.common.indicators import Indicators, IndicatorsFileBadFormat
from mvt.ios.modules.backup.backup_info import BackupInfo
from mvt.common.module import run_module


class TestBackupInfoModule:
    @pytest.fixture(scope="session", autouse=True)
    def set(self):
        init_setup()

    def test_manifest(self):
        m = BackupInfo(base_folder=get_artifact_folder(), log=logging)
        run_module(m)
        assert m.results["Build Version"] == "18C66"
        assert m.results["IMEI"] == '42'

