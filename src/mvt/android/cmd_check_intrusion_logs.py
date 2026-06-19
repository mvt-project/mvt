# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
from typing import Optional

from mvt.common.command import Command
from mvt.common.indicators import Indicators

from .modules.intrusion_logs import (
    INTRUSION_LOGS_MODULES,
    KNOWN_INTRUSION_LOG_EVENT_TYPES,
)
from .modules.intrusion_logs.base import IntrusionLogsModule

log = logging.getLogger(__name__)


class CmdAndroidCheckIntrusionLogs(Command):
    """Command to check Android Intrusion Logging files."""

    def __init__(
        self,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        ioc_files: Optional[list] = None,
        iocs: Optional[Indicators] = None,
        module_name: Optional[str] = None,
        serial: Optional[str] = None,
        module_options: Optional[dict] = None,
        hashes: Optional[bool] = False,
        sub_command: Optional[bool] = False,
        disable_version_check: bool = False,
        disable_indicator_check: bool = False,
    ) -> None:
        super().__init__(
            target_path=target_path,
            results_path=results_path,
            ioc_files=ioc_files,
            iocs=iocs,
            module_name=module_name,
            serial=serial,
            module_options=module_options,
            hashes=hashes,
            sub_command=sub_command,
            log=log,
            disable_version_check=disable_version_check,
            disable_indicator_check=disable_indicator_check,
        )

        self.name = "check-intrusion-logs"
        self.modules = INTRUSION_LOGS_MODULES
        self._all_events: dict[str, list[dict]] = {}

    def init(self) -> None:
        if not self.target_path:
            raise ValueError("No target path specified")

        if not os.path.isdir(self.target_path) and not (
            os.path.isfile(self.target_path)
            and self.target_path.lower().endswith(".zip")
        ):
            raise ValueError(
                f"Target path must be a directory or a .zip file: {self.target_path}"
            )

        self.log.info("Checking intrusion logs at path: %s", self.target_path)
        self._all_events = self._pre_load_events()

    def module_init(self, module: IntrusionLogsModule) -> None:  # type: ignore[override]
        module.il_events_by_type = self._all_events

    def finish(self) -> None:
        return

    def _pre_load_events(self) -> dict[str, list[dict]]:
        """Load and parse all advanced-log files once for reuse by all modules."""
        self.log.info("Pre-loading intrusion log files from: %s", self.target_path)

        loader = IntrusionLogsModule(
            target_path=self.target_path,
            log=self.log,
        )

        try:
            all_events = loader.load_all_events(self.target_path)
        except Exception as exc:
            self.log.error("Failed to pre-load events: %s", exc)
            return {}

        total_events = sum(len(events) for events in all_events.values())
        self.log.info(
            "Pre-loaded %d events across %d type(s); modules will reuse this data",
            total_events,
            len(all_events),
        )

        unknown_event_types = sorted(
            event_type
            for event_type in all_events
            if event_type not in KNOWN_INTRUSION_LOG_EVENT_TYPES
        )
        if unknown_event_types:
            self.log.warning(
                "Found unknown intrusion logging event type(s): %s. "
                "Please open an issue on GitHub so MVT can add support for them.",
                ", ".join(unknown_event_types),
            )

        return all_events
