# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import base64
import binascii
import datetime
import logging
from typing import Optional

from mvt.android.artifacts.dumpsys_adb import DumpsysADBArtifact
from mvt.common.module_types import ModuleResults
from mvt.common.utils import convert_datetime_to_iso

from .base import BugReportModule


class DumpsysADBState(DumpsysADBArtifact, BugReportModule):
    """This module extracts ADB key info."""

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        module_options: Optional[dict] = None,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[ModuleResults] = None,
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
        full_dumpsys = self._get_dumpstate_file()
        if not full_dumpsys:
            self.log.error(
                "Unable to find dumpstate file. "
                "Did you provide a valid bug report archive?"
            )
            return

        content = self.extract_dumpsys_section(
            full_dumpsys,
            b"DUMP OF SERVICE adb:",
            binary=True,
        )
        self.parse(content)
        if self.results:
            self.log.info(
                "Identified a total of %d trusted ADB keys",
                len(self.results[0].get("user_keys", [])),
            )

    @staticmethod
    def _key_material(public_key: object) -> str:
        if isinstance(public_key, bytes):
            public_key = public_key.decode("utf-8", errors="replace")
        if not isinstance(public_key, str):
            return ""
        return public_key.strip().split(" ", 1)[0]

    @staticmethod
    def _is_valid_key(public_key: str) -> bool:
        if not public_key:
            return False
        try:
            return bool(base64.b64decode(public_key, validate=True))
        except (binascii.Error, ValueError):
            return False

    @staticmethod
    def _parse_acquisition_time(value: object) -> Optional[datetime.datetime]:
        if not isinstance(value, str):
            return None
        try:
            timestamp = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if not timestamp.tzinfo:
            timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
        return timestamp.astimezone(datetime.timezone.utc)

    @staticmethod
    def _parse_last_connected(value: object) -> Optional[datetime.datetime]:
        try:
            return datetime.datetime.fromtimestamp(
                int(str(value)) / 1000,
                tz=datetime.timezone.utc,
            )
        except (OSError, OverflowError, TypeError, ValueError):
            return None

    def _trusted_keys(self) -> list[dict]:
        """Return unique trusted keys, preferring keystore connection metadata."""
        trusted_keys = []
        seen = set()
        for result in self.results:
            keystore = result.get("keystore", [])
            candidates = keystore if isinstance(keystore, list) else []
            candidates = [*candidates, *result.get("user_keys", [])]
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                key = self._key_material(candidate.get("key"))
                identity = key or repr(candidate)
                if identity in seen:
                    continue
                seen.add(identity)
                trusted_keys.append(candidate)
        return trusted_keys

    def check_indicators(self) -> None:
        if "androidqf_acquisition" not in self.module_options:
            return super().check_indicators()

        context = self.module_options.get("androidqf_acquisition")
        if not isinstance(context, dict):
            context = {}
        acquisition_key = self._key_material(context.get("adb_host_public_key"))
        if acquisition_key and not self._is_valid_key(acquisition_key):
            acquisition_key = ""
        acquisition_time = self._parse_acquisition_time(context.get("started"))
        cutoff = (
            acquisition_time - datetime.timedelta(days=1) if acquisition_time else None
        )

        for trusted_key in self._trusted_keys():
            key = self._key_material(trusted_key.get("key"))
            fingerprint = trusted_key.get("fingerprint") or "<unknown key>"
            user = trusted_key.get("user") or "unknown user"
            description = f"{fingerprint} ({user})"
            last_connected = self._parse_last_connected(
                trusted_key.get("last_connected")
            )
            event_time = (
                convert_datetime_to_iso(last_connected) if last_connected else ""
            )

            if not self._is_valid_key(key):
                self.alertstore.low(
                    f"Found an invalid trusted ADB host key: {description}",
                    event_time,
                    trusted_key,
                )
                continue

            if not acquisition_key:
                self.alertstore.low(
                    "Found a trusted ADB host key, but the AndroidQF acquisition "
                    f"does not include its host key: {description}",
                    event_time,
                    trusted_key,
                )
                continue

            if key != acquisition_key:
                self.alertstore.low(
                    "Found a trusted ADB host key different from the AndroidQF "
                    f"acquisition host: {description}",
                    event_time,
                    trusted_key,
                )
                continue

            if cutoff and last_connected and last_connected <= cutoff:
                self.alertstore.info(
                    "Found a trusted ADB host key last connected at least one day "
                    f"before the AndroidQF acquisition: {description}",
                    event_time,
                    trusted_key,
                )
