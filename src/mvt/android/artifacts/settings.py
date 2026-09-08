# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import re
from datetime import datetime
from typing import Optional, Sequence

from mvt.common.module_types import ModuleAtomicResult, ModuleSerializedResult
from mvt.common.utils import convert_datetime_to_iso

from .artifact import AndroidArtifact

ANDROID_DANGEROUS_SETTINGS = [
    {
        "description": "disabled Google Play Services apps verification",
        "key": "verifier_verify_adb_installs",
        "safe_value": "1",
    },
    {
        "description": "disabled Google Play Protect",
        "key": "package_verifier_enable",
        "safe_value": "1",
    },
    {
        "description": "disabled APK package verification",
        "key": "package_verifier_state",
        "safe_value": "1",
    },
    {
        "description": "disabled Google Play Protect",
        "key": "package_verifier_user_consent",
        "safe_value": "1",
    },
    {
        "description": "disabled Google Play Protect",
        "key": "upload_apk_enable",
        "safe_value": "1",
    },
    {
        "description": "disabled confirmation of adb apps installation",
        "key": "adb_install_need_confirm",
        "safe_value": "1",
    },
    {
        "description": "disabled sharing of security reports",
        "key": "send_security_reports",
        "safe_value": "1",
    },
    {
        "description": "disabled sharing of crash logs with manufacturer",
        "key": "samsung_errorlog_agree",
        "safe_value": "1",
    },
    {
        "description": "disabled applications errors reports",
        "key": "send_action_app_error",
        "safe_value": "1",
    },
    {
        "description": "enabled accessibility services",
        "key": "accessibility_enabled",
        "safe_value": "0",
    },
]

# dumpsys prints the fields of a setting record, and of a change history entry,
# always in this order and separated by a single space. After the value come
# `default:` and `defaultSystemSet:` when a default is recorded, then `tag:`;
# some vendor builds add whether the value survives a restore, either as
# `isValuePreservedInRestore:` or as a bare `notPreservedInRestore` token.
SETTING_FIELDS = (
    "_id",
    "name",
    "pkg",
    "value",
    "default",
    "defaultSystemSet",
    "tag",
    "isValuePreservedInRestore",
)
HISTORY_FIELDS = ("time", "mode", "oldValue", "newValue", "package")

NAMESPACE_PATTERN = re.compile(
    r"^(CONFIG|GLOBAL|SECURE|SYSTEM) SETTINGS \(user (\d+)\)$"
)
SECTION_END_PATTERN = re.compile(r"ending at: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")


class Settings(AndroidArtifact):
    """Parser for the `dumpsys settings` output.

    Every row of the settings provider becomes one result, keeping the fields
    dumpsys prints alongside the value: the row id, the package which recorded
    the setting, the default, the tag, and the change history. A setting name
    can appear more than once within a namespace, so results are a list rather
    than a mapping.
    """

    def serialize(self, result: ModuleAtomicResult) -> ModuleSerializedResult:
        records = []
        for entry in result.get("history", []):
            if not entry.get("timestamp"):
                continue

            records.append(
                {
                    "timestamp": entry["timestamp"],
                    "module": self.__class__.__name__,
                    "event": "settings_change",
                    "data": (
                        f"{result.get('namespace')} setting "
                        f'"{result.get("name")}" changed from '
                        f'"{entry.get("oldValue")}" to "{entry.get("newValue")}" '
                        f"by {entry.get('pkg')}"
                    ),
                }
            )

        return records

    def check_indicators(self) -> None:
        for result in self.results:
            name = result.get("name")
            value = result.get("value")
            for danger in ANDROID_DANGEROUS_SETTINGS:
                # Check if one of the dangerous settings is using an unsafe
                # value (different than the one specified).
                if danger["key"] != name or danger["safe_value"] == value:
                    continue

                history = result.get("history") or []
                self.alertstore.medium(
                    f'Found suspicious "{result.get("namespace")}" setting '
                    f'"{name} = {value}" ({danger["description"]})',
                    history[-1]["timestamp"] if history else "",
                    result,
                )
                break

    def parse(self, content: str) -> None:
        self.results: list[ModuleAtomicResult] = []
        section_end = self._parse_section_end(content)
        namespace: Optional[str] = None
        user: Optional[str] = None
        record_lines: list[str] = []
        history_lines: list[str] = []
        in_history = False

        def flush() -> None:
            nonlocal record_lines, history_lines, in_history
            if record_lines:
                self.results.append(
                    self._build_record(
                        namespace, user, record_lines, history_lines, section_end
                    )
                )
            record_lines = []
            history_lines = []
            in_history = False

        for line in content.splitlines():
            heading = NAMESPACE_PATTERN.match(line.strip())
            if heading:
                flush()
                namespace = heading.group(1).lower()
                user = heading.group(2)
                continue

            if line.startswith("--------- "):
                # dumpsys closes every section with a duration trailer.
                flush()
                namespace = None
                continue

            if namespace is None:
                continue

            if not line.strip():
                # dumpsys prints a blank line after every namespace block and
                # after a change history, and other dumps such as the
                # generation registry follow the last block, so a blank line
                # closes the record being read.
                flush()
                continue

            if line.startswith("_id:"):
                flush()
                record_lines = [line]
                continue

            if not record_lines:
                continue

            stripped = line.strip()
            if stripped.startswith("History ("):
                in_history = True
                continue

            if in_history:
                if stripped.startswith("time:"):
                    history_lines.append(stripped)
                elif stripped and history_lines:
                    # A history entry can be wrapped over several lines.
                    history_lines[-1] += " " + stripped
                continue

            # Anything else continues the value of the record being read.
            record_lines.append(line)

        flush()

    @staticmethod
    def _split_fields(text: str, keys: Sequence[str]) -> dict[str, str]:
        """Split the `key:value` fields of one record.

        Values are free-form and may contain spaces and newlines, so a field
        runs up to the start of the next key which is actually present. Keys
        dumpsys did not print are skipped.
        """
        fields: dict[str, str] = {}
        key = keys[0]
        if not text.startswith(f"{key}:"):
            return fields

        remainder = text[len(key) + 1 :]
        for next_key in keys[1:]:
            value, separator, rest = remainder.partition(f" {next_key}:")
            if separator:
                fields[key] = value
                key, remainder = next_key, rest

        fields[key] = remainder
        return fields

    @staticmethod
    def _parse_section_end(content: str) -> Optional[datetime]:
        """Return the time the settings section was dumped, if reported."""
        match = SECTION_END_PATTERN.search(content)
        if not match:
            return None

        try:
            return datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

    @staticmethod
    def _resolve_timestamp(
        value: str, section_end: Optional[datetime]
    ) -> Optional[str]:
        """Add the missing year to a `MM-DD HH:MM:SS.mmm` history timestamp.

        dumpsys prints the change history without a year, so it is resolved
        against the time the section was dumped: the most recent matching date
        at or before that time.
        """
        if section_end is None:
            return None

        try:
            partial = datetime.strptime(value, "%m-%d %H:%M:%S.%f")
            timestamp = partial.replace(year=section_end.year)
            if timestamp > section_end:
                timestamp = partial.replace(year=section_end.year - 1)
        except ValueError:
            return None

        return convert_datetime_to_iso(timestamp)

    def _parse_history(
        self, line: str, section_end: Optional[datetime]
    ) -> ModuleAtomicResult:
        fields = self._split_fields(line, HISTORY_FIELDS)
        return {
            "timestamp": self._resolve_timestamp(fields.get("time", ""), section_end),
            "oldValue": fields.get("oldValue"),
            "newValue": fields.get("newValue"),
            "pkg": fields.get("package"),
        }

    def _build_record(
        self,
        namespace: Optional[str],
        user: Optional[str],
        record_lines: list[str],
        history_lines: list[str],
        section_end: Optional[datetime],
    ) -> ModuleAtomicResult:
        text = "\n".join(record_lines).rstrip()
        # The bare `notPreservedInRestore` token has no `key:` shape and is
        # printed last, so peel it off before splitting the fields.
        head = text.removesuffix(" notPreservedInRestore")

        record: ModuleAtomicResult = {"namespace": namespace, "user": user}
        record.update(self._split_fields(head, SETTING_FIELDS))
        if head != text:
            record["isValuePreservedInRestore"] = "false"

        record["history"] = [
            self._parse_history(entry, section_end) for entry in history_lines
        ]
        return record
