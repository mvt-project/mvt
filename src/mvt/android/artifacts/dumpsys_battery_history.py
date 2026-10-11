# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import datetime
import re

from mvt.common.utils import convert_datetime_to_iso

from .artifact import AndroidArtifact


class DumpsysBatteryHistoryArtifact(AndroidArtifact):
    """Parser for package-related events in dumpsys batterystats history."""

    def check_indicators(self) -> None:
        if not self.indicators:
            return
        for result in self.results:
            package_name = result.get("package_name")
            if not package_name:
                continue
            ioc_match = self.indicators.check_app_id(package_name)
            if ioc_match:
                self.alertstore.critical(
                    ioc_match.message, "", result, matched_indicator=ioc_match.ioc
                )

    @staticmethod
    def _parse_wall_time(value: str) -> datetime.datetime | None:
        if re.fullmatch(r"\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+", value):
            value = f"1900-{value}"
        for date_format in (
            "%Y-%m-%d-%H-%M-%S-%f",
            "%Y-%m-%d-%H-%M-%S",
            "%Y-%m-%d %H:%M:%S.%f",
        ):
            try:
                return datetime.datetime.strptime(value, date_format)
            except ValueError:
                pass
        return None

    @staticmethod
    def _elapsed_seconds(value: str) -> float | None:
        if not value.startswith("+"):
            return None
        units = {"d": 86400, "h": 3600, "m": 60, "s": 1, "ms": 0.001}
        total = 0.0
        for number, unit in re.findall(r"(\d+)(ms|d|h|m|s)", value):
            total += int(number) * units[unit]
        return total

    @staticmethod
    def _package_from_name(name: str) -> str | None:
        clean = name.removeprefix("*walarm*:").removeprefix("*alarm*:")
        slash_parts = clean.split("/")
        if len(slash_parts) > 1:
            first = slash_parts[0].lstrip("@")
            if first.startswith(("com.", "org.", "net.")):
                return first
            for part in reversed(slash_parts[1:]):
                candidate = part.lstrip("@").split(":", 1)[0]
                if candidate.startswith(("com.", "org.", "net.")):
                    return candidate
        parts = clean.split(".")
        package_parts = []
        for part in parts:
            if part and part[0].islower():
                package_parts.append(part)
            else:
                break
        return ".".join(package_parts) if len(package_parts) >= 2 else None

    @staticmethod
    def _normalize_service(service: str) -> str:
        # WorkManager decorates jobs with one or more scheduler prefixes.
        if "@" in service:
            candidates = [part for part in service.split("@") if "/" in part]
            if candidates:
                return candidates[-1]
        return service

    def parse(self, data: str) -> None:
        self.results: list[dict[str, str | None]] = []
        anchor_time: datetime.datetime | None = None
        anchor_elapsed = 0.0
        has_history_heading = any(
            line.startswith("Battery History") for line in data.splitlines()
        )
        in_history = not has_history_heading

        for line in data.splitlines():
            stripped = line.strip()
            if line.startswith("Battery History"):
                if in_history:
                    break
                in_history = True
                continue
            if not in_history:
                continue
            if has_history_heading and not stripped:
                break
            reset_match = re.search(r"(?:RESET:)?TIME:\s*(\S+)", stripped)
            if reset_match:
                parsed_time = self._parse_wall_time(reset_match.group(1))
                if parsed_time is not None:
                    elapsed_token = stripped.split()[0]
                    anchor_elapsed = self._elapsed_seconds(elapsed_token) or 0.0
                    anchor_time = parsed_time
                continue

            fields = stripped.split()
            if not fields:
                continue
            if len(fields) > 1 and re.fullmatch(r"\d{2}-\d{2}", fields[0]):
                time_elapsed = " ".join(fields[:2])
                line_time = self._parse_wall_time(time_elapsed)
                elapsed = None
            else:
                time_elapsed = fields[0]
                elapsed = self._elapsed_seconds(time_elapsed)
                line_time = None

            timestamp = line_time
            if timestamp is None and anchor_time is not None and elapsed is not None:
                timestamp = anchor_time + datetime.timedelta(
                    seconds=elapsed - anchor_elapsed
                )

            def add(
                event: str, uid: str, service: str, package_name: str | None
            ) -> None:
                self.results.append(
                    {
                        "time_elapsed": time_elapsed,
                        "timestamp": convert_datetime_to_iso(timestamp)
                        if timestamp
                        else None,
                        "event": event,
                        "uid": uid,
                        "package_name": package_name,
                        "service": service,
                    }
                )

            for sign, uid, raw_service in re.findall(
                r"([+-])job=([^:\s]+):\"([^\"]+)\"", line
            ):
                service = self._normalize_service(raw_service)
                add(
                    "start_job" if sign == "+" else "end_job",
                    uid,
                    service,
                    self._package_from_name(service) or service.split("/", 1)[0],
                )

            for sign, uid, package_name in re.findall(
                r"([+-])top=([^:\s]+):\"([^\"]+)\"", line
            ):
                add(
                    "start_top" if sign == "+" else "end_top",
                    uid,
                    "",
                    package_name,
                )

            wake_match = re.search(r"\+wake_lock=([^:\s]+):\"([^\"]+)\"", line)
            if wake_match:
                wake_name = wake_match.group(2)
                add(
                    "wake",
                    wake_match.group(1),
                    wake_name,
                    self._package_from_name(wake_name),
                )
