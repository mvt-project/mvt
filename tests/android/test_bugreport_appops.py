# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
from pathlib import Path

from mvt.android.modules.bugreport.appops import Appops
from mvt.common.indicators import Indicators
from mvt.common.module import run_module

from ..utils import get_artifact_folder


class TestAppopsModule:
    def test_appops_parsing(self):
        fpath = os.path.join(get_artifact_folder(), "android_data/bugreport/")
        m = Appops(base_folder=fpath, log=logging, results=[])
        folder_files = []
        parent_path = Path(fpath).absolute().as_posix()
        for root, subdirs, subfiles in os.walk(os.path.abspath(fpath)):
            for file_name in subfiles:
                folder_files.append(os.path.relpath(os.path.join(root, file_name), parent_path))
        m.from_folder(fpath, folder_files)

        run_module(m)
        assert len(m.results) == 12
        assert len(m.timeline) == 16
        assert len(m.detected) == 0
