# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2025 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import csv
import inspect
import logging
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from .log import CRITICAL_ALERT, HIGH_ALERT, INFO_ALERT, LOW_ALERT, MEDIUM_ALERT
from .module_types import ModuleAtomicResult


class AlertLevel(Enum):
    INFORMATIONAL = 0
    LOW = 10
    MEDIUM = 20
    HIGH = 30
    CRITICAL = 40


@dataclass
class Alert:
    level: AlertLevel
    module: str
    message: str
    event_time: str
    event: ModuleAtomicResult


class AlertStore:
    def __init__(self, log: Optional[logging.Logger] = None) -> None:
        self.__alerts: List[Alert] = []
        self.__log = log

    def _get_calling_module(self) -> str:
        """
        Automatically detect the calling MVT module and return its slug.

        Walks up the call stack to find the first frame that belongs to an MVT module
        (artifact or extraction module) and extracts its slug.

        :return: Module slug string
        """
        frame = inspect.currentframe()
        try:
            # Walk up the call stack
            while frame is not None:
                frame = frame.f_back
                if frame is None:
                    break

                # Get the 'self' object from the frame's local variables
                frame_locals = frame.f_locals
                if "self" in frame_locals:
                    obj = frame_locals["self"]
                    # Check if it has a get_slug method (MVT modules have this)
                    if hasattr(obj, "get_slug") and callable(obj.get_slug):
                        try:
                            return obj.get_slug()
                        except Exception:
                            pass

            # Fallback: return "unknown" if we can't find the module
            return "unknown"
        finally:
            del frame

    @property
    def alerts(self) -> List[Alert]:
        return self.__alerts

    def add(self, alert: Alert) -> None:
        self.__alerts.append(alert)
        self.log(alert)

    def extend(self, alerts: List[Alert]) -> None:
        for alert in alerts:
            self.add(alert)

    def info(self, message: str, event_time: str, event: ModuleAtomicResult):
        self.add(
            Alert(
                level=AlertLevel.INFORMATIONAL,
                module=self._get_calling_module(),
                message=message,
                event_time=event_time,
                event=event,
            )
        )

    def low(self, message: str, event_time: str, event: ModuleAtomicResult):
        self.add(
            Alert(
                level=AlertLevel.LOW,
                module=self._get_calling_module(),
                message=message,
                event_time=event_time,
                event=event,
            )
        )

    def medium(self, message: str, event_time: str, event: ModuleAtomicResult):
        self.add(
            Alert(
                level=AlertLevel.MEDIUM,
                module=self._get_calling_module(),
                message=message,
                event_time=event_time,
                event=event,
            )
        )

    def high(self, message: str, event_time: str, event: ModuleAtomicResult):
        self.add(
            Alert(
                level=AlertLevel.HIGH,
                module=self._get_calling_module(),
                message=message,
                event_time=event_time,
                event=event,
            )
        )

    def critical(self, message: str, event_time: str, event: ModuleAtomicResult):
        self.add(
            Alert(
                level=AlertLevel.CRITICAL,
                module=self._get_calling_module(),
                message=message,
                event_time=event_time,
                event=event,
            )
        )

    def log(self, alert: Alert) -> None:
        if not self.__log:
            return

        if not alert.message:
            return

        if alert.level == AlertLevel.INFORMATIONAL:
            self.__log.log(INFO_ALERT, alert.message)
        elif alert.level == AlertLevel.LOW:
            self.__log.log(LOW_ALERT, alert.message)
        elif alert.level == AlertLevel.MEDIUM:
            self.__log.log(MEDIUM_ALERT, alert.message)
        elif alert.level == AlertLevel.HIGH:
            self.__log.log(HIGH_ALERT, alert.message)
        elif alert.level == AlertLevel.CRITICAL:
            self.__log.log(CRITICAL_ALERT, alert.message)

    def log_latest(self) -> None:
        self.log(self.__alerts[-1])

    def count(self, level: AlertLevel) -> int:
        count = 0
        for alert in self.__alerts:
            if alert.level == level:
                count += 1

        return count

    def as_json(self) -> List[Dict[str, Any]]:
        alerts = []
        for alert in self.__alerts:
            alert_dict = asdict(alert)
            # This is required because an Enum is not JSON serializable.
            alert_dict["level"] = alert.level.name
            alerts.append(alert_dict)

        return alerts

    def save_timeline(self, timeline_path: str) -> None:
        with open(timeline_path, "a+", encoding="utf-8") as handle:
            csvoutput = csv.writer(
                handle,
                delimiter=",",
                quotechar='"',
                quoting=csv.QUOTE_ALL,
                escapechar="\\",
            )
            csvoutput.writerow(["Event Time", "Module", "Message", "Event"])

            timed_alerts = []
            for alert in self.alerts:
                if not alert.event_time:
                    continue

                timed_alerts.append(asdict(alert))

            for event in sorted(
                timed_alerts,
                key=lambda x: x["event_time"] if x["event_time"] is not None else "",
            ):
                csvoutput.writerow(
                    [
                        event.get("event_time"),
                        event.get("module"),
                        event.get("message"),
                        event.get("event"),
                    ]
                )
