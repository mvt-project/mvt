# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import json
import sqlite3
import tempfile
from pathlib import Path, PurePosixPath

from mvt.android.artifacts.browser_history import (
    BrowserHistoryArtifact,
    open_browser_history_database,
    validate_manifest_database,
)

from .base import AndroidQFModule


class BrowserHistory(BrowserHistoryArtifact, AndroidQFModule):
    """Extract browser visits collected by AndroidQF."""

    supported_commands = (("android", "check-androidqf"),)

    def _find_manifest(self) -> str | None:
        manifests = [
            file_path
            for file_path in self.files
            if file_path.replace("\\", "/").endswith("browser_history/manifest.json")
        ]
        if not manifests:
            return None
        if len(manifests) > 1:
            self.log.warning(
                "Found multiple browser history manifests; using %s", manifests[0]
            )
        return manifests[0]

    def _stage_database(
        self, archive_path: str, prefix: str, temporary_path: Path
    ) -> Path:
        available_files = {
            file_path.replace("\\", "/"): file_path for file_path in self.files
        }
        normalized_path = str(PurePosixPath(prefix, archive_path))
        source_path = available_files.get(normalized_path)
        if not source_path:
            raise FileNotFoundError(archive_path)

        staged_path = temporary_path / "History"
        staged_path.write_bytes(self._get_file_content(source_path))
        for suffix in ("-wal", "-shm"):
            sidecar = available_files.get(normalized_path + suffix)
            if sidecar:
                Path(f"{staged_path}{suffix}").write_bytes(
                    self._get_file_content(sidecar)
                )
        return staged_path

    def run(self) -> None:
        manifest_path = self._find_manifest()
        if not manifest_path:
            self.log.info("No AndroidQF browser history manifest found")
            return

        try:
            manifest = json.loads(self._get_file_content(manifest_path))
        except (json.JSONDecodeError, OSError, TypeError, UnicodeDecodeError) as exc:
            self.log.error("Unable to read browser history manifest: %s", exc)
            return

        if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
            self.log.error("Unsupported AndroidQF browser history manifest")
            return
        databases = manifest.get("databases", [])
        if not isinstance(databases, list):
            self.log.error("Invalid AndroidQF browser history database list")
            return

        normalized_manifest = manifest_path.replace("\\", "/")
        marker = "browser_history/manifest.json"
        prefix = normalized_manifest[: -len(marker)].rstrip("/")

        for raw_database in databases:
            try:
                database = validate_manifest_database(raw_database)
                with tempfile.TemporaryDirectory(prefix="mvt_browser_history_") as temp:
                    staged_path = self._stage_database(
                        database["archive_path"], prefix, Path(temp)
                    )
                    connection = open_browser_history_database(staged_path)
                    try:
                        self._parse_browser_history(
                            connection,
                            browser=database["browser"],
                            package=database["package"],
                            profile=database["profile"],
                            source_path=database["device_path"],
                        )
                    finally:
                        connection.close()
            except (
                FileNotFoundError,
                OSError,
                OverflowError,
                sqlite3.Error,
                TypeError,
                ValueError,
            ) as exc:
                self.log.error("Unable to parse browser history database: %s", exc)

        self.log.info(
            "Extracted a total of %d browser history items", len(self.results)
        )
