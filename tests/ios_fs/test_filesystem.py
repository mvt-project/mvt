# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
import logging
import ntpath
from types import SimpleNamespace

from mvt.common.indicators import Indicators
from mvt.common.module import run_module
from mvt.ios.modules.fs import filesystem
from mvt.ios.modules.fs.filesystem import Filesystem

from ..utils import get_ios_backup_folder


class TestFilesystem:
    def test_windows_paths_are_normalized_for_indicators(
        self, monkeypatch, indicators_factory
    ):
        m = Filesystem(target_path=r"C:\dump")
        m.indicators = indicators_factory(
            file_paths=["matched/directory"], processes=["matched"]
        )
        monkeypatch.setattr(
            filesystem,
            "os",
            SimpleNamespace(
                sep="\\",
                path=ntpath,
                walk=lambda _: [(r"C:\dump\matched", ["directory"], ["file.txt"])],
                stat=lambda _: SimpleNamespace(st_mtime=0),
            ),
        )

        m.run()
        m.check_indicators()

        assert {result["path"] for result in m.results} == {
            "matched/directory",
            "matched/file.txt",
        }
        assert len(m.alertstore.alerts) == 3

    def test_filesystem(self):
        m = Filesystem(target_path=get_ios_backup_folder())
        run_module(m)
        assert len(m.results) == 23
        assert len(m.timeline) == 23
        assert len(m.alertstore.alerts) == 0

    def test_detection(self, indicator_file):
        m = Filesystem(target_path=get_ios_backup_folder())
        ind = Indicators(log=logging.getLogger())
        ind.parse_stix2(indicator_file)
        # Adds a filename that exist in the folder
        ind.ioc_collections[0]["processes"].append(
            "64d0019cb3d46bfc8cce545a8ba54b93e7ea9347"
        )
        m.indicators = ind
        run_module(m)
        assert len(m.results) == 23
        assert len(m.timeline) == 23
        assert len(m.alertstore.alerts) == 1
