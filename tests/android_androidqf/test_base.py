# Mobile Verification Toolkit (MVT)
# Copyright (c) 2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import zipfile

import pytest

from mvt.android.modules.androidqf.base import AndroidQFModule


@pytest.mark.parametrize("prefix", ["", "./", "acquisition/", "outer/acquisition/"])
@pytest.mark.parametrize(
    "pattern, filename",
    [
        ("*/packages.json", "packages.json"),
        ("*/getprop.txt", "getprop.txt"),
        ("*/ps.txt", "ps.txt"),
        ("*/settings_*.txt", "settings_global.txt"),
        ("*/files.json", "files.json"),
        ("*/logs/*", "logs/logcat.txt"),
        ("*/mounts.json", "mounts.json"),
        ("*/root_binaries.json", "root_binaries.json"),
    ],
)
def test_artifact_lookup_preserves_archive_names(tmp_path, prefix, pattern, filename):
    member = prefix + filename
    with zipfile.ZipFile(tmp_path / "acquisition.zip", "w") as archive:
        archive.writestr(member, b"artifact")
        archive.writestr(prefix + "unrelated.txt", b"unrelated")
        module = AndroidQFModule()
        module.from_zip(archive, archive.namelist())

        assert module._get_files_by_pattern(pattern) == [member]
        assert module._get_file_content(member) == b"artifact"


def test_artifact_lookup_preserves_windows_paths():
    module = AndroidQFModule()
    module.from_dir("parent", [r"acquisition\logs\logcat.txt"])

    assert module._get_files_by_pattern("*/logs/*") == [r"acquisition\logs\logcat.txt"]


def test_artifact_lookup_preserves_order_without_duplicates():
    module = AndroidQFModule()
    module.files = [
        "acquisition/settings_global.txt",
        "settings_secure.txt",
        "./settings_system.txt",
        "not_settings_global.txt",
        "settings_global.txt.bak",
    ]

    assert module._get_files_by_pattern("*/settings_*.txt") == module.files[:3]
    assert module._get_files_by_pattern("settings_secure.txt") == [
        "settings_secure.txt"
    ]
    assert module._get_files_by_pattern("*/missing.txt") == []
