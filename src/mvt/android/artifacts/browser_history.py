# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import sqlite3
import shutil
import tempfile
from pathlib import Path
from typing import Any

from mvt.common.module_types import ModuleAtomicResult, ModuleSerializedResult
from mvt.common.utils import convert_chrometime_to_datetime, convert_datetime_to_iso

from .artifact import AndroidArtifact


class BrowserHistoryArtifact(AndroidArtifact):
    """Shared Chromium History database parsing and result handling."""

    def _parse_browser_history(
        self,
        connection: sqlite3.Connection,
        *,
        browser: str,
        package: str,
        profile: str,
        source_path: str,
    ) -> None:
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                SELECT
                    urls.id,
                    urls.url,
                    urls.title,
                    urls.visit_count,
                    urls.typed_count,
                    visits.id,
                    visits.visit_time,
                    visits.from_visit,
                    visits.transition
                FROM urls
                JOIN visits ON visits.url = urls.id
                ORDER BY visits.visit_time;
                """
            )
            for row in cursor:
                timestamp = int(row[6])
                self.results.append(
                    {
                        "id": row[0],
                        "url": row[1],
                        "title": row[2],
                        "visit_count": row[3],
                        "typed_count": row[4],
                        "visit_id": row[5],
                        "timestamp": timestamp,
                        "isodate": convert_datetime_to_iso(
                            convert_chrometime_to_datetime(timestamp)
                        ),
                        "redirect_source": row[7],
                        "transition": row[8],
                        "browser": browser,
                        "package": package,
                        "profile": profile,
                        "source_path": source_path,
                    }
                )
        finally:
            cursor.close()

    def serialize(self, record: ModuleAtomicResult) -> ModuleSerializedResult:
        return {
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": "browser_history",
            "data": (
                f"{record['browser']} visit to {record['url']} "
                f"(visit ID: {record['visit_id']}, profile: {record['profile']})"
            ),
        }

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result, match in zip(
            self.results,
            self.indicators.check_url_batches(
                [[result["url"]] for result in self.results]
            ),
        ):
            if match:
                self.alertstore.critical(
                    match.message, "", result, matched_indicator=match.ioc
                )

    def collect_url_results(self) -> None:
        for result in self.results:
            self.add_url_result(result["url"], result.get("isodate"), "browser_history")


class TemporarySQLiteConnection(sqlite3.Connection):
    temporary_directory: tempfile.TemporaryDirectory | None = None

    def close(self) -> None:
        try:
            super().close()
        finally:
            if self.temporary_directory:
                self.temporary_directory.cleanup()
                self.temporary_directory = None


def open_browser_history_database(database_path: Path) -> sqlite3.Connection:
    """Open a staged History database without modifying forensic evidence."""
    database_uri = database_path.resolve().as_uri()
    if not Path(f"{database_path}-wal").is_file():
        return sqlite3.connect(f"{database_uri}?mode=ro&immutable=1", uri=True)

    temporary_directory = tempfile.TemporaryDirectory(prefix="mvt_sqlite_")
    temporary_path = Path(temporary_directory.name) / database_path.name
    shutil.copy2(database_path, temporary_path)
    for suffix in ("-wal", "-shm"):
        sidecar = Path(f"{database_path}{suffix}")
        if sidecar.is_file():
            shutil.copy2(sidecar, Path(f"{temporary_path}{suffix}"))

    try:
        connection = sqlite3.connect(
            f"{temporary_path.resolve().as_uri()}?mode=ro",
            uri=True,
            factory=TemporarySQLiteConnection,
        )
    except Exception:
        temporary_directory.cleanup()
        raise
    connection.temporary_directory = temporary_directory
    return connection


def validate_manifest_database(database: Any) -> dict[str, Any]:
    if not isinstance(database, dict):
        raise ValueError("database entry is not an object")

    required = ("browser", "package", "profile", "device_path", "archive_path")
    for field in required:
        if not isinstance(database.get(field), str) or not database[field]:
            raise ValueError(f"database entry has invalid {field}")

    archive_path = database["archive_path"]
    path = Path(archive_path)
    if (
        "\\" in archive_path
        or path.is_absolute()
        or ".." in path.parts
        or path.parts[:1] != ("browser_history",)
    ):
        raise ValueError(f"unsafe browser history archive path: {archive_path}")
    return database
