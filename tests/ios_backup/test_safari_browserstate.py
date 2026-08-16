# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import shutil

import pytest

from mvt.common.indicators import Indicators
from mvt.common.module import run_module
from mvt.ios.modules.mixed.safari_browserstate import SafariBrowserState

from ..utils import add_backup_manifest_entry, get_ios_backup_folder

# fileID of HomeDomain::Library/Safari/BrowserState.db in the test backup.
DEFAULT_BROWSER_STATE_FILE_ID = "3a47b0981ed7c10f3e2800aa66bac96a3b5db28e"
PROFILE_UUID = "00000000-0000-4000-A000-000000000001"
PROFILE_BROWSER_STATE_FILE_ID = "bb00000000000000000000000000000000000001"


@pytest.fixture
def backup_with_safari_profile(tmp_path):
    """An iTunes backup where a Safari profile has its own browser state."""
    backup_path = tmp_path / "backup"
    shutil.copytree(get_ios_backup_folder(), backup_path)

    profile_db = (
        backup_path / PROFILE_BROWSER_STATE_FILE_ID[:2] / PROFILE_BROWSER_STATE_FILE_ID
    )
    profile_db.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        backup_path / DEFAULT_BROWSER_STATE_FILE_ID[:2] / DEFAULT_BROWSER_STATE_FILE_ID,
        profile_db,
    )
    add_backup_manifest_entry(
        backup_path,
        PROFILE_BROWSER_STATE_FILE_ID,
        "AppDomain-com.apple.mobilesafari",
        f"Library/Safari/Profiles/{PROFILE_UUID}/BrowserState.db",
    )

    return str(backup_path)


class TestSafariBrowserStateModule:
    def test_parsing(self):
        m = SafariBrowserState(target_path=get_ios_backup_folder())
        m.is_backup = True
        run_module(m)
        assert len(m.results) == 1
        assert len(m.timeline) == 1
        assert len(m.alertstore.alerts) == 0

    def test_parsing_backup_with_profile(self, backup_with_safari_profile):
        m = SafariBrowserState(target_path=backup_with_safari_profile)
        m.is_backup = True
        run_module(m)

        # Both the default profile and the named profile are extracted.
        assert len(m.results) == 2
        assert len({result["safari_browser_state_db"] for result in m.results}) == 2

    def test_detection(self, indicator_file):
        m = SafariBrowserState(target_path=get_ios_backup_folder())
        m.is_backup = True
        ind = Indicators(log=logging.getLogger())
        ind.parse_stix2(indicator_file)
        # Adds a file that exists in the manifest.
        ind.ioc_collections[0]["domains"].append("en.wikipedia.org")
        m.indicators = ind
        run_module(m)
        assert len(m.alertstore.alerts) == 1
        assert len(m.results) == 1
        assert m.results[0]["tab_url"] == "https://en.wikipedia.org/wiki/NSO_Group"
