# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2025 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import csv
import logging
from enum import Enum
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

from .log import INFO_ALERT, LOW_ALERT, HIGH_ALERT, CRITICAL_ALERT, MEDIUM_ALERT
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

    @property
    def alerts(self) -> List[Alert]:
        return self.__alerts

    def add(self, alert: Alert) -> None:
        self.__alerts.append(alert)

    def extend(self, alerts: List[Alert]) -> None:
        self.__alerts.extend(alerts)

    def info(
        self, module: str, message: str, event_time: str, event: ModuleAtomicResult
    ):
        self.add(
            Alert(
                level=AlertLevel.INFORMATIONAL,
                module=module,
                message=message,
                event_time=event_time,
                event=event,
            )
        )

    def low(
        self, module: str, message: str, event_time: str, event: ModuleAtomicResult
    ):
        self.add(
            Alert(
                level=AlertLevel.LOW,
                module=module,
                message=message,
                event_time=event_time,
                event=event,
            )
        )

    def medium(
        self, module: str, message: str, event_time: str, event: ModuleAtomicResult
    ):
        self.add(
            Alert(
                level=AlertLevel.MEDIUM,
                module=module,
                message=message,
                event_time=event_time,
                event=event,
            )
        )

    def high(
        self, module: str, message: str, event_time: str, event: ModuleAtomicResult
    ):
        self.add(
            Alert(
                level=AlertLevel.HIGH,
                module=module,
                message=message,
                event_time=event_time,
                event=event,
            )
        )

    def critical(
        self, module: str, message: str, event_time: str, event: ModuleAtomicResult
    ):
        self.add(
            Alert(
                level=AlertLevel.CRITICAL,
                module=module,
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
