# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional

from mvt.android.parsers import parse_dumpsys_network_interfaces

from .base import BugReportModule


class NetworkInterfaces(BugReportModule):
    """This module extracts network interfaces from 'ip link' command."""

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        fast_mode: Optional[bool] = False,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[list] = None
    ) -> None:
        super().__init__(file_path=file_path, target_path=target_path,
                         results_path=results_path, fast_mode=fast_mode,
                         log=log, results=results)

        self.results = {} if not results else results

    def run(self) -> None:
        content = self._get_dumpstate_file()
        if not content:
            self.log.error("Unable to find dumpstate file. "
                           "Did you provide a valid bug report archive?")
            return

        lines = []
        in_getprop = False

        for line in content.decode(errors="ignore").splitlines():
            if line.strip().startswith("------ NETWORK INTERFACES"):
                in_getprop = True
                continue

            if not in_getprop:
                continue

            if line.strip().startswith("------"):
                break

            lines.append(line)

        self.results = parse_dumpsys_network_interfaces("\n".join(lines))

        self.log.info("Extracted information about %d Android network interfaces",
                      len(self.results))
