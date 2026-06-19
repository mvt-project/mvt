# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from pathlib import Path

from mvt.android.modules.androidqf.aqf_files import AQFFiles
from mvt.common.module import run_module

from ..utils import get_android_androidqf, list_files


class TestAndroidqfFilesAnalysis:
    def test_androidqf_files(self):
        data_path = get_android_androidqf()
        m = AQFFiles(target_path=data_path, log=logging)
        files = list_files(data_path)
        parent_path = Path(data_path).absolute().parent.as_posix()
        m.from_dir(parent_path, files)
        run_module(m)
        assert len(m.results) == 3
        assert len(m.timeline) == 6
        assert len(m.alertstore.alerts) == 0
