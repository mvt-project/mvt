# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import zipfile
from pathlib import Path

from mvt.android.modules.androidqf.getprop import Getprop
from mvt.common.indicators import Indicators
from mvt.common.module import run_module

from ..utils import get_android_androidqf, get_artifact, list_files


class TestAndroidqfGetpropAnalysis:
    def test_androidqf_getprop(self):
        data_path = get_android_androidqf()
        m = Getprop(target_path=data_path, log=logging)
        files = list_files(data_path)
        parent_path = Path(data_path).absolute().parent.as_posix()
        m.from_folder(parent_path, files)
        run_module(m)
        assert len(m.results) == 10
        assert m.results[0]["name"] == "dalvik.vm.appimageformat"
        assert m.results[0]["value"] == "lz4"
        assert len(m.timeline) == 0
        assert len(m.detected) == 0

    def test_getprop_parsing_zip(self):
        fpath = get_artifact("androidqf.zip")
        m = Getprop(target_path=fpath, log=logging)
        archive = zipfile.ZipFile(fpath)
        m.from_zip_file(archive, archive.namelist())
        run_module(m)
        assert len(m.results) == 10
        assert m.results[0]["name"] == "dalvik.vm.appimageformat"
        assert m.results[0]["value"] == "lz4"
        assert len(m.timeline) == 0
        assert len(m.detected) == 0

    def test_androidqf_getprop_detection(self, indicator_file):
        data_path = get_android_androidqf()
        m = Getprop(target_path=data_path, log=logging)
        files = list_files(data_path)
        parent_path = Path(data_path).absolute().parent.as_posix()
        m.from_folder(parent_path, files)
        ind = Indicators(log=logging.getLogger())
        ind.parse_stix2(indicator_file)
        ind.ioc_collections[0]["android_property_names"].append("dalvik.vm.heapmaxfree")
        m.indicators = ind
        run_module(m)
        assert len(m.results) == 10
        assert len(m.detected) == 1
        assert m.detected[0]["name"] == "dalvik.vm.heapmaxfree"
