# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from pathlib import Path

from mvt.android.modules.androidqf.aqf_files import AQFFiles
from mvt.common.module import run_module
from mvt.android.parsers.protobuf_parsers import parse_files_records
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

    def test_androidqf_files_from_protobuf(self):
        data_path = get_android_androidqf()

        # test protobuf parser per-se
        data = (Path(data_path) / "files.pb").read_bytes()
        records = parse_files_records(data)
        assert len(records) == 3
        assert records[0]["path"] == "/sdcard/.profig.os"
        assert records[0]["modified_time"] == 1593109532

        # test module with protobuf file
        m = AQFFiles(target_path=data_path, log=logging)
        files = ["androidqf/files.pb"]
        parent_path = Path(data_path).absolute().parent.as_posix()
        m.from_dir(parent_path, files)
        run_module(m)
        assert len(m.results) == 3
