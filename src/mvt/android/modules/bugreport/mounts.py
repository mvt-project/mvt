# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.

import re

from mvt.android.artifacts.mounts import Mounts as MountsArtifact

from .base import BugReportModule


class Mounts(MountsArtifact, BugReportModule):
    """Extract and deduplicate process mount namespaces from mountinfo."""

    def run(self) -> None:
        mount_files = self._get_files_by_pattern("FS/proc/*/mountinfo")
        if not mount_files:
            mount_files = self._get_files_by_pattern("*/proc/*/mountinfo")
        unique: dict[tuple, dict] = {}
        for file_path in mount_files:
            pid_match = re.search(r"/proc/(\d+)/mountinfo$", file_path)
            if not pid_match:
                continue
            entries = self.parse_mountinfo(
                self._get_file_content(file_path).decode("utf-8", errors="replace"),
                int(pid_match.group(1)),
            )
            for entry in entries:
                identity = (
                    entry["major_minor"],
                    entry["root"],
                    entry["mount_point"],
                    entry["device"],
                    entry["filesystem_type"],
                    entry["mount_options"],
                )
                if identity in unique:
                    unique[identity]["process_ids"].extend(entry["process_ids"])
                else:
                    unique[identity] = entry
        self.results = list(unique.values())
        self.log.info("Extracted %d unique mount records", len(self.results))
