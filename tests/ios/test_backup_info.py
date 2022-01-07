import logging

from mvt.ios.modules.backup.backup_info import BackupInfo
from mvt.common.module import run_module

from ..utils import get_backup_folder


class TestBackupInfoModule:
    def test_manifest(self):
        m = BackupInfo(base_folder=get_backup_folder(), log=logging)
        run_module(m)
        assert m.results["Build Version"] == "18C66"
        assert m.results["IMEI"] == '42'
