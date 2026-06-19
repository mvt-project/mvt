# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from pathlib import Path

import pytest

from mvt.android.modules.androidqf.root_binaries import RootBinaries
from mvt.common.module import run_module

from ..utils import get_android_androidqf, list_files


@pytest.fixture()
def data_path():
    return get_android_androidqf()


@pytest.fixture()
def parent_data_path(data_path):
    return Path(data_path).absolute().parent.as_posix()


@pytest.fixture()
def file_list(data_path):
    return list_files(data_path)


@pytest.fixture()
def module(parent_data_path, file_list):
    m = RootBinaries(target_path=parent_data_path, log=logging)
    m.from_dir(parent_data_path, file_list)
    return m


class TestAndroidqfRootBinaries:
    def test_root_binaries_detection(self, module):
        run_module(module)

        # Should find 4 root binaries from the test file
        assert len(module.results) == 4
        assert len(module.alertstore.alerts) == 4

        # Check that all results are detected as indicators
        binary_paths = [result["path"] for result in module.results]
        assert "/system/bin/su" in binary_paths
        assert "/system/xbin/busybox" in binary_paths
        assert "/data/local/tmp/magisk" in binary_paths
        assert "/system/bin/magiskhide" in binary_paths

    def test_root_binaries_descriptions(self, module):
        run_module(module)

        # Check that binary descriptions are correctly identified
        su_result = next((r for r in module.results if "su" in r["binary_name"]), None)
        assert su_result is not None
        assert "SuperUser binary" in su_result["description"]

        busybox_result = next(
            (r for r in module.results if "busybox" in r["binary_name"]), None
        )
        assert busybox_result is not None
        assert "BusyBox utilities" in busybox_result["description"]

        magisk_result = next(
            (r for r in module.results if r["binary_name"] == "magisk"), None
        )
        assert magisk_result is not None
        assert "Magisk root framework" in magisk_result["description"]

        magiskhide_result = next(
            (r for r in module.results if "magiskhide" in r["binary_name"]), None
        )
        assert magiskhide_result is not None
        assert "Magisk hide utility" in magiskhide_result["description"]

    def test_root_binaries_warnings(self, caplog, module):
        run_module(module)

        # Check that warnings are logged for each root binary found
        assert 'Found root binary "su" at path "/system/bin/su"' in caplog.text
        assert (
            'Found root binary "busybox" at path "/system/xbin/busybox"' in caplog.text
        )
        assert (
            'Found root binary "magisk" at path "/data/local/tmp/magisk"' in caplog.text
        )
        assert (
            'Found root binary "magiskhide" at path "/system/bin/magiskhide"'
            in caplog.text
        )
        assert "Device shows signs of rooting with 4 root binaries found" in caplog.text

    def test_serialize_method(self, module):
        run_module(module)

        # Test that serialize method works correctly
        if module.results:
            serialized = module.serialize(module.results[0])
            assert serialized["module"] == "RootBinaries"
            assert serialized["event"] == "root_binary_found"
            assert "Root binary found:" in serialized["data"]

    def test_no_root_binaries_file(self, parent_data_path):
        # Test behavior when no root_binaries.json file is present
        empty_file_list = []
        m = RootBinaries(target_path=parent_data_path, log=logging)
        m.from_dir(parent_data_path, empty_file_list)

        run_module(m)

        assert len(m.results) == 0
        assert len(m.alertstore.alerts) == 0
