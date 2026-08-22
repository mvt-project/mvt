# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.

from mvt.android.artifacts.processes import Processes as ProcessesArtifact

from .base import BugReportModule


class Processes(ProcessesArtifact, BugReportModule):
    """Extract the process and thread table from dumpstate."""

    def run(self) -> None:
        data = self._get_dumpstate_file()
        if not data:
            self.log.error("Unable to find dumpstate file")
            return
        section = self.extract_command_section(
            data.decode("utf-8", errors="replace"),
            "------ PROCESSES AND THREADS",
        )
        self.parse(section)
        self.log.info("Identified %d running process threads", len(self.results))
