# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from datetime import datetime, timedelta
from typing import Optional

from mvt.android.parsers import parse_getprop

from .base import BugReportModule


class Getprop(BugReportModule):
    """This module extracts device properties from getprop command."""

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        fast_mode: bool = False,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[list] = None,
    ) -> None:
        super().__init__(
            file_path=file_path,
            target_path=target_path,
            results_path=results_path,
            fast_mode=fast_mode,
            log=log,
            results=results,
        )

        self.results = {} if not results else results

    def run(self) -> None:
        content = self._get_dumpstate_file()
        if not content:
            self.log.error(
                "Unable to find dumpstate file. "
                "Did you provide a valid bug report archive?"
            )
            return

        lines = []
        in_getprop = False

        for line in content.decode(errors="ignore").splitlines():
            if line.strip().startswith("------ SYSTEM PROPERTIES"):
                in_getprop = True
                continue

            if not in_getprop:
                continue

            if line.strip() == "------":
                break

            lines.append(line)

        self.results = parse_getprop("\n".join(lines))

        # Alert if phone is outdated.
        for entry in self.results:
            if entry["name"] == "ro.build.version.security_patch":
                security_patch = entry["value"]
                patch_date = datetime.strptime(security_patch, "%Y-%m-%d")
                if (datetime.now() - patch_date) > timedelta(days=6 * 30):
                    self.log.warning(
                        "This phone has not received security updates "
                        "for more than six months (last update: %s)",
                        security_patch,
                    )

        self.log.info("Extracted %d Android system properties", len(self.results))
