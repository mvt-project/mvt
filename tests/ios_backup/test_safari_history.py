# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import shutil
import sqlite3
from pathlib import Path

import pytest

from mvt.common.indicators import Indicators
from mvt.common.module import run_module
from mvt.ios.modules.mixed.safari_history import SafariHistory

from ..utils import add_backup_manifest_entry, get_ios_backup_folder

# fileID of HomeDomain::Library/Safari/History.db in the test backup.
DEFAULT_HISTORY_FILE_ID = "1a0e7afc19d307da602ccdcece51af33afe92c53"
PROFILE_UUID = "00000000-0000-4000-A000-000000000001"
PROFILE_HISTORY_FILE_ID = "aa00000000000000000000000000000000000001"

# example.org is already a test indicator, so use domains that do not match.
DEFAULT_URL = "https://default.example.net/visited-page"
PROFILE_URL = "https://profile.example.net/visited-page"


def create_history_db(path, url):
    """Create a minimal Safari History.db holding a single visit."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE history_items (id INTEGER PRIMARY KEY, url TEXT);
        CREATE TABLE history_visits (
            id INTEGER PRIMARY KEY,
            history_item INTEGER,
            visit_time REAL,
            redirect_source INTEGER,
            redirect_destination INTEGER
        );
        """
    )
    conn.execute("INSERT INTO history_items VALUES (1, ?);", (url,))
    conn.execute("INSERT INTO history_visits VALUES (1, 1, 726100000.0, NULL, NULL);")
    conn.commit()
    conn.close()


@pytest.fixture
def backup_with_safari_profile(tmp_path):
    """An iTunes backup where Safari has both a default and a named profile."""
    backup_path = tmp_path / "backup"
    shutil.copytree(get_ios_backup_folder(), backup_path)

    # The default profile's database ships empty, so give it a visit to make
    # sure the profile lookup does not replace the pre-existing one.
    create_history_db(
        backup_path / DEFAULT_HISTORY_FILE_ID[:2] / DEFAULT_HISTORY_FILE_ID,
        DEFAULT_URL,
    )

    create_history_db(
        backup_path / PROFILE_HISTORY_FILE_ID[:2] / PROFILE_HISTORY_FILE_ID,
        PROFILE_URL,
    )
    add_backup_manifest_entry(
        backup_path,
        PROFILE_HISTORY_FILE_ID,
        "AppDomain-com.apple.mobilesafari",
        f"Library/Safari/Profiles/{PROFILE_UUID}/History.db",
    )

    return str(backup_path)


@pytest.fixture
def fs_dump_with_safari_profile(tmp_path):
    """A filesystem dump where Safari has both a default and a named profile."""
    safari_path = tmp_path / "private" / "var" / "mobile" / "Library" / "Safari"
    profile_path = safari_path / "Profiles" / PROFILE_UUID
    profile_path.mkdir(parents=True)

    create_history_db(safari_path / "History.db", DEFAULT_URL)
    create_history_db(profile_path / "History.db", PROFILE_URL)

    return str(tmp_path)


class TestSafariHistoryModule:
    def test_parsing(self):
        m = SafariHistory(target_path=get_ios_backup_folder())
        m.is_backup = True
        run_module(m)
        assert len(m.results) == 0
        assert len(m.alertstore.alerts) == 0

    def test_parsing_backup_with_profile(self, backup_with_safari_profile):
        m = SafariHistory(target_path=backup_with_safari_profile)
        m.is_backup = True
        run_module(m)

        # Both the default profile and the named profile are extracted.
        assert len(m.results) == 2
        assert {result["url"] for result in m.results} == {DEFAULT_URL, PROFILE_URL}
        assert len({result["safari_history_db"] for result in m.results}) == 2

    def test_parsing_fs_dump_with_profile(self, fs_dump_with_safari_profile):
        m = SafariHistory(target_path=fs_dump_with_safari_profile)
        m.is_fs_dump = True
        run_module(m)

        assert len(m.results) == 2
        assert {result["url"] for result in m.results} == {DEFAULT_URL, PROFILE_URL}

    def test_redirect_ids_are_scoped_to_database(self, fs_dump_with_safari_profile):
        safari_path = (
            Path(fs_dump_with_safari_profile)
            / "private"
            / "var"
            / "mobile"
            / "Library"
            / "Safari"
        )
        with sqlite3.connect(safari_path / "History.db") as conn:
            conn.execute(
                "UPDATE history_items SET url = ? WHERE id = 1;",
                ("http://safe.example.com/start",),
            )
            conn.execute(
                "INSERT INTO history_items VALUES (2, ?);",
                ("https://safe.example.com/end",),
            )
            conn.execute(
                "UPDATE history_visits SET redirect_destination = 2 WHERE id = 1;"
            )
            conn.execute(
                "INSERT INTO history_visits VALUES (2, 2, 726100000.1, 1, NULL);"
            )

        profile_db = safari_path / "Profiles" / PROFILE_UUID / "History.db"
        with sqlite3.connect(profile_db) as conn:
            # Visit IDs are local to each database and commonly overlap.
            conn.execute("UPDATE history_visits SET id = 2 WHERE id = 1;")

        m = SafariHistory(target_path=fs_dump_with_safari_profile)
        m.is_fs_dump = True
        run_module(m)

        assert len(m.results) == 3
        assert len(m.alertstore.alerts) == 0

    def test_detection_in_profile(self, backup_with_safari_profile, indicator_file):
        """An indicator only visited inside a Safari profile still alerts."""
        m = SafariHistory(target_path=backup_with_safari_profile)
        m.is_backup = True
        ind = Indicators(log=logging.getLogger())
        ind.parse_stix2(indicator_file)
        ind.ioc_collections[0]["domains"].append("profile.example.net")
        m.indicators = ind
        run_module(m)

        assert len(m.alertstore.alerts) == 1
        assert m.alertstore.alerts[0].event["url"] == PROFILE_URL
