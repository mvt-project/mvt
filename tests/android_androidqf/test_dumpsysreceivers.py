# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from pathlib import Path

from mvt.android.modules.androidqf.dumpsys_receivers import DumpsysReceivers
from mvt.common.module import run_module

from ..utils import get_android_androidqf, list_files


class TestDumpsysReceiversModule:
    def test_parsing(self):
        data_path = get_android_androidqf()
        m = DumpsysReceivers(target_path=data_path)
        files = list_files(data_path)
        parent_path = Path(data_path).absolute().parent.as_posix()
        m.from_folder(parent_path, files)
        run_module(m)
        assert len(m.results) == 4
        assert len(m.detected) == 0
