# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import json
import logging
import os
from pathlib import PurePosixPath
from typing import Optional

from mvt.common.module_types import ModuleAtomicResult, ModuleResults

from .base import AndroidQFModule


class MagiskModules(AndroidQFModule):
    """Parse Magisk module metadata collected by AndroidQF."""

    MAX_MODULE_PROP_SIZE = 1024 * 1024

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        module_options: Optional[dict] = None,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[ModuleResults] = None,
    ) -> None:
        super().__init__(
            file_path=file_path,
            target_path=target_path,
            results_path=results_path,
            module_options=module_options,
            log=log,
            results=results,
        )

    @staticmethod
    def _parse_module_prop(content: str) -> dict[str, str]:
        properties = {}
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            if not key:
                continue
            properties[key] = value.strip()

        return properties

    def _find_archive_file(self, archive_path: object) -> Optional[str]:
        if not isinstance(archive_path, str) or not archive_path:
            return None
        if "\\" in archive_path:
            return None

        normalized = PurePosixPath(archive_path)
        if (
            normalized.is_absolute()
            or ".." in normalized.parts
            or len(normalized.parts) < 3
            or normalized.parts[0] != "magisk_modules"
            or normalized.name != "module.prop"
        ):
            return None

        expected = normalized.as_posix()
        matches = []
        for file_path in self.files:
            normalized_file = file_path.replace("\\", "/")
            if normalized_file == expected or normalized_file.endswith(f"/{expected}"):
                matches.append(file_path)

        if len(matches) != 1:
            return None
        return matches[0]

    def _read_module_prop(self, file_path: str) -> Optional[str]:
        try:
            if self.archive:
                if self.archive.getinfo(file_path).file_size > self.MAX_MODULE_PROP_SIZE:
                    self.log.warning('Skipping oversized Magisk property file "%s"', file_path)
                    return None
            else:
                full_path = os.path.join(self.parent_path or "", file_path)
                if os.path.getsize(full_path) > self.MAX_MODULE_PROP_SIZE:
                    self.log.warning('Skipping oversized Magisk property file "%s"', file_path)
                    return None

            return self._get_file_content(file_path).decode("utf-8", errors="replace")
        except (KeyError, OSError):
            self.log.warning('Unable to read Magisk property file "%s"', file_path)
            return None

    def _find_manifest(self) -> Optional[str]:
        marker = "magisk_modules/manifest.json"
        manifests = []
        for file_path in self.files:
            normalized = file_path.replace("\\", "/")
            if normalized == marker or normalized.endswith(f"/{marker}"):
                manifests.append(file_path)
        if not manifests:
            return None
        if len(manifests) > 1:
            self.log.warning(
                "Found multiple Magisk module manifests; using %s", manifests[0]
            )
        return manifests[0]

    def run(self) -> None:
        manifest_path = self._find_manifest()
        if not manifest_path:
            self.log.debug("No Magisk module manifest found in AndroidQF data.")
            return

        try:
            manifest = json.loads(self._get_file_content(manifest_path))
        except (json.JSONDecodeError, OSError, TypeError, UnicodeDecodeError) as exc:
            self.log.error("Unable to parse Magisk module manifest: %s", exc)
            return

        if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
            self.log.error("Unsupported AndroidQF Magisk module manifest.")
            return
        if not isinstance(manifest.get("modules"), list):
            self.log.error("Magisk module manifest has an invalid structure.")
            return

        for entry in manifest["modules"]:
            if not isinstance(entry, dict):
                self.log.warning("Skipping invalid Magisk module manifest entry.")
                continue

            state_files = entry.get("state_files", [])
            if not isinstance(state_files, list) or not all(
                isinstance(item, str) for item in state_files
            ):
                state_files = []
                state_files_complete = False
            else:
                state_files_complete = entry.get("state_files_complete") is True

            state_set = set(state_files)
            result: ModuleAtomicResult = {
                "device_path": entry.get("device_path"),
                "directory_name": entry.get("directory_name"),
                "module_prop_status": entry.get("module_prop_status"),
                "state_files": state_files,
                "state_files_complete": state_files_complete,
                "disabled": "disable" in state_set if state_files_complete else None,
                "removal_pending": "remove" in state_set
                if state_files_complete
                else None,
                "update_pending": "update" in state_set
                if state_files_complete
                else None,
                "properties": {},
            }

            if entry.get("module_prop_status") == "collected":
                file_path = self._find_archive_file(entry.get("module_prop_path"))
                if not file_path:
                    self.log.warning(
                        'Magisk property path "%s" is missing or unsafe.',
                        entry.get("module_prop_path"),
                    )
                else:
                    content = self._read_module_prop(file_path)
                    if content is not None:
                        result["properties"] = self._parse_module_prop(content)

            properties: dict[str, str] = result["properties"]
            result.update(
                {
                    "id": properties.get("id"),
                    "name": properties.get("name"),
                    "version": properties.get("version"),
                    "version_code": properties.get("versionCode"),
                    "author": properties.get("author"),
                    "description": properties.get("description"),
                    "update_json": properties.get("updateJson"),
                }
            )
            self.results.append(result)

        self.log.info("Identified a total of %d Magisk modules", len(self.results))
