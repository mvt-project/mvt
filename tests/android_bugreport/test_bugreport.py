# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import os
from pathlib import Path

from mvt.android.modules.bugreport.appops import Appops
from mvt.android.modules.bugreport.getprop import Getprop
from mvt.android.modules.bugreport.packages import Packages
from mvt.common.module import run_module

from ..utils import get_artifact_folder


class TestBugreportAnalysis:
    def launch_bug_report_module(self, module):
        fpath = os.path.join(get_artifact_folder(), "android_data/bugreport/")
        m = module(target_path=fpath)
        folder_files = []
        parent_path = Path(fpath).absolute().as_posix()
        for root, subdirs, subfiles in os.walk(os.path.abspath(fpath)):
            for file_name in subfiles:
                folder_files.append(
                    os.path.relpath(os.path.join(root, file_name), parent_path)
                )
        m.from_folder(fpath, folder_files)
        run_module(m)
        return m

    def test_appops_module(self):
        m = self.launch_bug_report_module(Appops)
        assert len(m.results) == 12
        assert len(m.timeline) == 16
        assert len(m.detected) == 0

    def test_packages_module(self):
        m = self.launch_bug_report_module(Packages)
        assert len(m.results) == 2
        assert (
            m.results[0]["package_name"]
            == "com.samsung.android.provider.filterprovider"
        )
        assert m.results[1]["package_name"] == "com.instagram.android"
        assert len(m.results[0]["permissions"]) == 4
        assert len(m.results[1]["permissions"]) == 32

    def test_getprop_module(self):
        m = self.launch_bug_report_module(Getprop)
        assert len(m.results) == 0
