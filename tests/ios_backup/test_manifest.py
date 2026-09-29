# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import gc
import logging
import shutil
import warnings

import pytest

from mvt.common.indicators import Indicators
from mvt.common.module import run_module
from mvt.ios.modules.base import IOSExtraction
from mvt.ios.modules.backup.manifest import Manifest

from ..utils import get_ios_backup_folder

# fileID of HomeDomain::Library/SMS/sms.db in the test backup. It is one of the
# few files the test backup actually stores.
SMS_FILE_ID = "3d0d7e5fb2ce288813306e4d4636395e047a3d28"


@pytest.fixture
def backup_without_stored_files(tmp_path):
    """A copy of the test backup with every stored file removed.

    The test backup only ships a handful of the files its manifest lists, so
    dropping what it does store leaves a backup where every regular file the
    manifest mentions is missing from the folder.
    """
    backup_path = tmp_path / "backup"
    shutil.copytree(get_ios_backup_folder(), backup_path)

    for file_id_folder in backup_path.iterdir():
        if not file_id_folder.is_dir():
            continue
        for backup_file in file_id_folder.iterdir():
            backup_file.unlink()

    return str(backup_path)


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

    def test_manifest_flags_the_files_missing_from_an_incomplete_backup(self):
        m = Manifest(target_path=get_ios_backup_folder())
        run_module(m)

        missing = [result for result in m.results if result.get("missing")]
        # The test backup only stores a handful of the files its manifest
        # lists, and every one of the rest is a regular file (flags 1).
        assert len(missing) == 1079
        assert all(result["flags"] == 1 for result in missing)

        stored = [result for result in m.results if result["file_id"] == SMS_FILE_ID]
        assert len(stored) == 1
        assert "missing" not in stored[0]

    def test_manifest_flags_every_stored_file_removed_from_the_backup_folder(
        self, backup_without_stored_files
    ):
        m = Manifest(target_path=backup_without_stored_files)
        run_module(m)

        missing = [result for result in m.results if result.get("missing")]
        assert len(missing) == 1089

    def test_manifest_flags_a_file_removed_from_the_backup_folder(self, tmp_path):
        backup_path = tmp_path / "backup"
        shutil.copytree(get_ios_backup_folder(), backup_path)
        (backup_path / SMS_FILE_ID[:2] / SMS_FILE_ID).unlink()

        m = Manifest(target_path=str(backup_path))
        run_module(m)

        removed = [result for result in m.results if result["file_id"] == SMS_FILE_ID]
        assert len(removed) == 1
        assert removed[0]["missing"] is True

    def test_detection(self, indicator_file):
        m = Manifest(target_path=get_ios_backup_folder())
        ind = Indicators(log=logging.getLogger())
        ind.parse_stix2(indicator_file)
        ind.ioc_collections[0]["file_names"].append("com.apple.CoreBrightness.plist")
        m.indicators = ind
        run_module(m)
        assert len(m.alertstore.alerts) == 1
