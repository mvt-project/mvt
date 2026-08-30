# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.

from mvt.android.artifacts.settings import Settings as SettingsArtifact

from .base import BugReportModule


class Settings(SettingsArtifact, BugReportModule):
    """Extract all SettingsProvider namespaces and users."""

    def run(self) -> None:
        data = self._get_dumpstate_file()
        if not data:
            self.log.error("Unable to find dumpstate file")
            return
        section = self.extract_dumpsys_section(
            data.decode("utf-8", errors="replace"), "DUMP OF SERVICE settings:"
        )
        self.parse(section)
        count = sum(len(settings) for settings in self.results.values())
        self.log.info("Identified %d Android settings", count)
