# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from mvt.common.module import run_module
from mvt.ios.modules.backup.backup_info import BackupInfo

from ..utils import get_ios_backup_folder


class TestBackupInfoModule:
    def test_manifest(self):
        m = BackupInfo(target_path=get_ios_backup_folder())
        run_module(m)
        assert m.results["Build Version"] == "18C66"
        assert m.results["IMEI"] == "42"
