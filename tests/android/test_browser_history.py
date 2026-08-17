# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import json
import sqlite3
import zipfile
from pathlib import Path

import pytest

from mvt.android.modules.androidqf.browser_history import (
    BrowserHistory as AndroidQFBrowserHistory,
)
from mvt.android.modules.fs.browser_history import BrowserHistory as FSBrowserHistory
from mvt.android.cmd_check_fs import CmdAndroidCheckFS

CHROME_TIME = 13_348_540_800_000_000
URL = "https://example.org/path"


def create_history_database(path: Path, *, url: str = URL) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE urls (
                id INTEGER PRIMARY KEY,
                url TEXT,
                title TEXT,
                visit_count INTEGER,
                typed_count INTEGER
            );
            CREATE TABLE visits (
                id INTEGER PRIMARY KEY,
                url INTEGER,
                visit_time INTEGER,
                from_visit INTEGER,
                transition INTEGER
            );
            """
        )
        connection.execute("INSERT INTO urls VALUES (1, ?, 'Example', 1, 0)", (url,))
        connection.execute(
            "INSERT INTO visits VALUES (7, 1, ?, 0, 805306368)",
            (CHROME_TIME,),
        )


def manifest(database_paths: list[tuple[str, str]]) -> dict:
    return {
        "schema_version": 1,
        "status": "collected",
        "databases": [
            {
                "browser": "Chrome",
                "package": package,
                "profile": "Default",
                "device_path": f"/data/data/{package}/app_chrome/Default/History",
                "archive_path": archive_path,
                "sidecars": [],
            }
            for package, archive_path in database_paths
        ],
    }


@pytest.mark.parametrize("use_zip", [False, True])
def test_androidqf_browser_history_directory_and_zip(tmp_path, use_zip):
    source_database = tmp_path / "source" / "History"
    create_history_database(source_database)
    archive_path = "browser_history/com.android.chrome/Default/History"
    manifest_data = manifest([("com.android.chrome", archive_path)])

    module = AndroidQFBrowserHistory()
    if use_zip:
        acquisition_path = tmp_path / "acquisition.zip"
        with zipfile.ZipFile(acquisition_path, "w") as archive:
            archive.write(source_database, archive_path)
            archive.writestr("browser_history/manifest.json", json.dumps(manifest_data))
        with zipfile.ZipFile(acquisition_path) as archive:
            module.from_zip(archive, archive.namelist())
            module.run()
    else:
        acquisition = tmp_path / "acquisition"
        database_path = acquisition / archive_path
        database_path.parent.mkdir(parents=True)
        database_path.write_bytes(source_database.read_bytes())
        manifest_path = acquisition / "browser_history" / "manifest.json"
        manifest_path.write_text(json.dumps(manifest_data))
        files = [
            path.relative_to(tmp_path).as_posix()
            for path in acquisition.rglob("*")
            if path.is_file()
        ]
        module.from_dir(str(tmp_path), files)
        module.run()

    assert len(module.results) == 1
    assert module.results[0]["url"] == URL
    assert module.results[0]["browser"] == "Chrome"
    assert module.results[0]["source_path"].endswith("/History")
    module.collect_url_results()
    module.to_timeline()
    assert module.url_results[0]["url"] == URL
    assert module.timeline[0]["event"] == "browser_history"


def test_androidqf_browser_history_isolates_malformed_database(tmp_path, caplog):
    acquisition = tmp_path / "acquisition"
    good_archive_path = "browser_history/com.android.chrome/Default/History"
    bad_archive_path = "browser_history/com.brave.browser/Default/History"
    create_history_database(acquisition / good_archive_path)
    bad_path = acquisition / bad_archive_path
    bad_path.parent.mkdir(parents=True)
    bad_path.write_bytes(b"not sqlite")
    manifest_path = acquisition / "browser_history" / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            manifest(
                [
                    ("com.brave.browser", bad_archive_path),
                    ("com.android.chrome", good_archive_path),
                ]
            )
        )
    )

    module = AndroidQFBrowserHistory()
    files = [
        path.relative_to(tmp_path).as_posix()
        for path in acquisition.rglob("*")
        if path.is_file()
    ]
    module.from_dir(str(tmp_path), files)
    module.run()

    assert [result["url"] for result in module.results] == [URL]
    assert "Unable to parse browser history database" in caplog.text


def test_androidqf_browser_history_rejects_unsafe_manifest_path(tmp_path, caplog):
    acquisition = tmp_path / "acquisition"
    manifest_path = acquisition / "browser_history" / "manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(manifest([("com.android.chrome", "browser_history/../secret")]))
    )
    module = AndroidQFBrowserHistory()
    module.from_dir(str(tmp_path), [manifest_path.relative_to(tmp_path).as_posix()])

    module.run()

    assert module.results == []
    assert "unsafe browser history archive path" in caplog.text


def test_filesystem_browser_history_reads_wal_only_visit(tmp_path):
    database_path = tmp_path / "History"
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.executescript(
        """
        CREATE TABLE urls (
            id INTEGER PRIMARY KEY,
            url TEXT,
            title TEXT,
            visit_count INTEGER,
            typed_count INTEGER
        );
        CREATE TABLE visits (
            id INTEGER PRIMARY KEY,
            url INTEGER,
            visit_time INTEGER,
            from_visit INTEGER,
            transition INTEGER
        );
        """
    )
    connection.commit()
    connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    connection.execute("INSERT INTO urls VALUES (1, ?, 'WAL', 1, 0)", (URL,))
    connection.execute(
        "INSERT INTO visits VALUES (8, 1, ?, 0, 805306368)", (CHROME_TIME,)
    )
    connection.commit()
    try:
        assert Path(f"{database_path}-wal").stat().st_size > 0
        module = FSBrowserHistory(target_path=str(database_path))
        module.run()
    finally:
        connection.close()

    assert [result["url"] for result in module.results] == [URL]
    assert module.results[0]["browser"] == "Chromium"


def test_android_check_fs_finds_all_supported_browser_paths(tmp_path):
    for index, relative_path in enumerate(
        (
            "data/data/com.android.chrome/app_chrome/Default/History",
            "data/data/com.brave.browser/app_chrome/Default/History",
            "data/data/com.microsoft.emmx/app_chrome/Default/History",
            "data/data/com.sec.android.app.sbrowser/app_sbrowser/Default/History",
        )
    ):
        create_history_database(
            tmp_path / relative_path, url=f"https://example.org/{index}"
        )

    command = CmdAndroidCheckFS(target_path=str(tmp_path), module_name="BrowserHistory")
    command.run()

    assert len(command.executed) == 1
    assert {result["package"] for result in command.executed[0].results} == {
        "com.android.chrome",
        "com.brave.browser",
        "com.microsoft.emmx",
        "com.sec.android.app.sbrowser",
    }
    assert len(command.url_results) == 4
    assert len(command.timeline) == 4
