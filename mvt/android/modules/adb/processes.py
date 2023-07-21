# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional

from .base import AndroidExtraction
from mvt.android.modules.detection_mixins import ProcessDetectionMixin


class Processes(ProcessDetectionMixin, AndroidExtraction):
    """This module extracts details on running processes."""

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

    def run(self) -> None:
        self._adb_connect()

        output = self._adb_command("ps -A")

        for line in output.splitlines()[1:]:
            line = line.strip()
            if line == "":
                continue

            fields = line.split()
            proc = {
                "user": fields[0],
                "pid": fields[1],
                "parent_pid": fields[2],
                "vsize": fields[3],
                "rss": fields[4],
            }

            # Sometimes WCHAN is empty, so we need to re-align output fields.
            if len(fields) == 8:
                proc["wchan"] = ""
                proc["pc"] = fields[5]
                proc["name"] = fields[7]
            elif len(fields) == 9:
                proc["wchan"] = fields[5]
                proc["pc"] = fields[6]
                proc["name"] = fields[8]

            self.results.append(proc)

        self._adb_disconnect()

        self.log.info("Extracted records on a total of %d processes", len(self.results))
