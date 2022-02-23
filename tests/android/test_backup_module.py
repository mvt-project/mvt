# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os

from mvt.android.modules.backup.sms import SMS
from mvt.common.module import run_module

from ..utils import get_android_backup_folder


class TestBackupModule:
    def test_module_folder(self):
        fpath = get_android_backup_folder()
        mod = SMS(base_folder=fpath, log=logging)
        run_module(mod)
        assert len(mod.results) == 1
        assert len(mod.results[0]["links"]) == 1
        assert mod.results[0]["links"][0] == "https://google.com/"

    def test_module_file(self):
        fpath = os.path.join(get_android_backup_folder(), "backup.ab")
        mod = SMS(base_folder=fpath, log=logging)
        run_module(mod)
        assert len(mod.results) == 1
        assert len(mod.results[0]["links"]) == 1
