# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import json
import logging
from typing import Optional

from .base import AndroidQFModule


class RootBinaries(AndroidQFModule):
    """This module analyzes root_binaries.json for root binaries found by androidqf."""

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        module_options: Optional[dict] = None,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[list] = None,
    ) -> None:
        super().__init__(
            file_path=file_path,
            target_path=target_path,
            results_path=results_path,
            module_options=module_options,
            log=log,
            results=results,
        )

    def serialize(self, record: dict) -> dict:
        return {
            "timestamp": record.get("timestamp"),
            "module": self.__class__.__name__,
            "event": "root_binary_found",
            "data": f"Root binary found: {record['path']} (binary: {record['binary_name']})",
        }

    def check_indicators(self) -> None:
        """Check for indicators of device rooting."""
        if not self.results:
            return

        # All found root binaries are considered indicators of rooting
        for result in self.results:
            self.alertstore.high(
                f'Found root binary "{result["binary_name"]}" at path "{result["path"]}"',
                "",
                result,
            )
            self.alertstore.log_latest()

        if self.results:
            self.log.warning(
                "Device shows signs of rooting with %d root binaries found",
                len(self.results),
            )

    def run(self) -> None:
        """Run the root binaries analysis."""
        root_binaries_files = self._get_files_by_pattern("*/root_binaries.json")

        if not root_binaries_files:
            self.log.info("No root_binaries.json file found")
            return

        rawdata = self._get_file_content(root_binaries_files[0]).decode(
            "utf-8", errors="ignore"
        )

        try:
            root_binary_paths = json.loads(rawdata)
        except json.JSONDecodeError as e:
            self.log.error("Failed to parse root_binaries.json: %s", e)
            return

        if not isinstance(root_binary_paths, list):
            self.log.error("Expected root_binaries.json to contain a list of paths")
            return

        # Known root binary names that might be found and their descriptions
        # This maps the binary name to a human-readable description
        known_root_binaries = {
            "su": "SuperUser binary",
            "busybox": "BusyBox utilities",
            "supersu": "SuperSU root management",
            "Superuser.apk": "Superuser app",
            "KingoUser.apk": "KingRoot app",
            "SuperSu.apk": "SuperSU app",
            "magisk": "Magisk root framework",
            "magiskhide": "Magisk hide utility",
            "magiskinit": "Magisk init binary",
            "magiskpolicy": "Magisk policy binary",
        }

        for path in root_binary_paths:
            if not path or not isinstance(path, str):
                continue

            # Extract binary name from path
            binary_name = path.split("/")[-1].lower()

            # Check if this matches a known root binary by exact name match
            description = "Unknown root binary"
            for known_binary in known_root_binaries:
                if binary_name == known_binary.lower():
                    description = known_root_binaries[known_binary]
                    break

            result = {
                "path": path.strip(),
                "binary_name": binary_name,
                "description": description,
            }

            self.results.append(result)

        self.log.info("Found %d root binaries", len(self.results))
