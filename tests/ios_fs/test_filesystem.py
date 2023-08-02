# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
import logging

import pytest

from mvt.common.indicators import Indicators
from mvt.common.module import run_module
from mvt.ios.modules.fs.filesystem import Filesystem

from ..utils import delete_tmp_db_files, get_ios_backup_folder


@pytest.fixture()
def cleanup_tmp_artifacts():
    ios_backup_folder = get_ios_backup_folder()
    delete_tmp_db_files(ios_backup_folder)
    return


class TestFilesystem:
    def test_filesystem(self, cleanup_tmp_artifacts):
        m = Filesystem(target_path=get_ios_backup_folder())
        run_module(m)
        assert len(m.results) == 15
        assert len(m.timeline) == 15
        assert len(m.detected) == 0

    def test_detection(self, indicator_file, cleanup_tmp_artifacts):
        m = Filesystem(target_path=get_ios_backup_folder())
        ind = Indicators(log=logging.getLogger())
        ind.parse_stix2(indicator_file)
        # Adds a filename that exist in the folder
        ind.ioc_collections[0]["processes"].append(
            "64d0019cb3d46bfc8cce545a8ba54b93e7ea9347"
        )
        m.indicators = ind
        run_module(m)
        assert len(m.results) == 15
        assert len(m.timeline) == 15
        assert len(m.detected) == 1
