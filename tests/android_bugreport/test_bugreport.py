# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import os
from pathlib import Path

from mvt.android.modules.bugreport.dumpsys_appops import DumpsysAppops
from mvt.android.modules.bugreport.dumpsys_getprop import DumpsysGetProp
from mvt.android.modules.bugreport.dumpsys_packages import DumpsysPackages
from mvt.android.modules.bugreport.tombstones import Tombstones
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
        m.from_dir(fpath, folder_files)
        run_module(m)
        return m

    def test_appops_module(self):
        m = self.launch_bug_report_module(DumpsysAppops)
        assert len(m.results) == 12
        assert len(m.timeline) == 16

        detected_by_ioc = [
            detected for detected in m.detected if detected.get("matched_indicator")
        ]
        assert len(m.detected) == 1  # Hueristic detection for suspicious permissions
        assert len(detected_by_ioc) == 0

    def test_packages_module(self):
        m = self.launch_bug_report_module(DumpsysPackages)
        assert len(m.results) == 2
        assert (
            m.results[0]["package_name"]
            == "com.samsung.android.provider.filterprovider"
        )
        assert m.results[1]["package_name"] == "com.instagram.android"
        assert len(m.results[0]["permissions"]) == 4
        assert len(m.results[1]["permissions"]) == 32

    def test_getprop_module(self):
        m = self.launch_bug_report_module(DumpsysGetProp)
        assert len(m.results) == 0

    def test_tombstones_modules(self):
        m = self.launch_bug_report_module(Tombstones)
        assert len(m.results) == 2
        assert m.results[1]["pid"] == 3559
