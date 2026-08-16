# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import gc
import logging
import warnings

from mvt.common.indicators import Indicators
from mvt.common.module import run_module
from mvt.ios.modules.base import IOSExtraction
from mvt.ios.modules.backup.manifest import Manifest

from ..utils import get_ios_backup_folder


class TestIOSExtraction:
    def test_get_backup_files_from_manifest_closes_connection(self):
        m = IOSExtraction(target_path=get_ios_backup_folder())

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ResourceWarning)
            files = list(m._get_backup_files_from_manifest(domain="CameraRollDomain"))
            gc.collect()

        assert files
        assert not [
            warning
            for warning in caught
            if issubclass(warning.category, ResourceWarning)
            and "unclosed database" in str(warning.message)
        ]


class TestManifestModule:
    def test_manifest(self):
        m = Manifest(target_path=get_ios_backup_folder())
        run_module(m)
        assert len(m.results) == 3721
        assert len(m.timeline) == 5881
        assert len(m.alertstore.alerts) == 0

    def test_detection(self, indicator_file):
        m = Manifest(target_path=get_ios_backup_folder())
        ind = Indicators(log=logging.getLogger())
        ind.parse_stix2(indicator_file)
        ind.ioc_collections[0]["file_names"].append("com.apple.CoreBrightness.plist")
        m.indicators = ind
        run_module(m)
        assert len(m.alertstore.alerts) == 1
