# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import gc
import logging
import os
import shutil
import warnings
from pathlib import Path

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
    @pytest.mark.parametrize("link_directory", [False, True], ids=["file", "directory"])
    @pytest.mark.parametrize("inside_backup", [False, True], ids=["outside", "inside"])
    def test_stored_file_inventory_matches_symlink_resolution(
        self, tmp_path, link_directory, inside_backup
    ):
        backup_path = tmp_path / "backup"
        backup_path.mkdir()
        destination = (backup_path if inside_backup else tmp_path) / "contents"
        destination.mkdir()
        (destination / SMS_FILE_ID).write_bytes(b"backup file")
        bucket = backup_path / SMS_FILE_ID[:2]
        try:
            if link_directory:
                bucket.symlink_to(destination, target_is_directory=True)
            else:
                bucket.mkdir()
                (bucket / SMS_FILE_ID).symlink_to(destination / SMS_FILE_ID)
        except OSError:
            pytest.skip("creating symbolic links is not permitted on this system")

        m = IOSExtraction(target_path=str(backup_path))
        assert bool(m._get_backup_file_from_id(SMS_FILE_ID)) is inside_backup
        assert m._get_stored_backup_file_ids() == (
            {SMS_FILE_ID} if inside_backup else set()
        )

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

    @pytest.mark.parametrize("failed_folder", ["", "3d"], ids=["root", "bucket"])
    def test_manifest_skips_missing_check_when_inventory_fails(
        self, monkeypatch, caplog, failed_folder
    ):
        backup_path = Path(get_ios_backup_folder())
        failed_path = backup_path / failed_folder
        scandir = os.scandir

        def fail_listing(path):
            if Path(path) == failed_path:
                raise PermissionError("cannot list backup folder")
            return scandir(path)

        monkeypatch.setattr(os, "scandir", fail_listing)
        m = Manifest(target_path=str(backup_path))
        with caplog.at_level(logging.INFO):
            m.run()

        assert len(m.results) == 3721
        assert m._get_backup_file_from_id(SMS_FILE_ID) is not None
        assert all("missing" not in result for result in m.results)
        assert "Skipping the missing-file check" in caplog.text
        assert "The backup might be incomplete" not in caplog.text

    def test_manifest_ignores_unreadable_unrelated_folders(self, tmp_path, monkeypatch):
        backup_path = tmp_path / "backup"
        shutil.copytree(get_ios_backup_folder(), backup_path)
        unrelated = backup_path / "notes"
        unrelated.mkdir()
        scandir = os.scandir

        def fail_listing(path):
            if Path(path) == unrelated:
                raise PermissionError("cannot list unrelated folder")
            return scandir(path)

        monkeypatch.setattr(os, "scandir", fail_listing)
        m = Manifest(target_path=str(backup_path))
        m.run()

        assert sum(bool(result.get("missing")) for result in m.results) == 1079
        stored = next(
            result for result in m.results if result["file_id"] == SMS_FILE_ID
        )
        assert "missing" not in stored

    @pytest.mark.parametrize("wrong_folder", ["ab", "notes"])
    def test_manifest_flags_files_in_the_wrong_folder(self, tmp_path, wrong_folder):
        backup_path = tmp_path / "backup"
        shutil.copytree(get_ios_backup_folder(), backup_path)
        destination = backup_path / wrong_folder
        destination.mkdir(exist_ok=True)
        (backup_path / SMS_FILE_ID[:2] / SMS_FILE_ID).rename(destination / SMS_FILE_ID)

        m = Manifest(target_path=str(backup_path))
        m.run()

        assert m._get_backup_file_from_id(SMS_FILE_ID) is None
        moved = next(result for result in m.results if result["file_id"] == SMS_FILE_ID)
        assert moved["missing"] is True
        assert sum(bool(result.get("missing")) for result in m.results) == 1080

    def test_detection(self, indicator_file):
        m = Manifest(target_path=get_ios_backup_folder())
        ind = Indicators(log=logging.getLogger())
        ind.parse_stix2(indicator_file)
        ind.ioc_collections[0]["file_names"].append("com.apple.CoreBrightness.plist")
        m.indicators = ind
        run_module(m)
        assert len(m.alertstore.alerts) == 1
