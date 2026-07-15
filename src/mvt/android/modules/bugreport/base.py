# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# See the file 'LICENSE' for usage and copying permissions, or find a copy at
#   https://github.com/mvt-project/mvt/blob/main/LICENSE
import datetime
import fnmatch
import io
import logging
import os
import re
from pathlib import Path
from typing import List, Optional
from zipfile import ZipFile

from mvt.android.artifacts.artifact import AndroidArtifact
from mvt.common.module import ModuleResults, MVTModule


_DUMPSTATE_BYTES_CACHE_KEY = ("android_bugreport", "dumpstate", "bytes")
_DUMPSTATE_SECTIONS_CACHE_KEY = ("android_bugreport", "dumpstate", "sections")
_SYSTEM_PROPERTIES_SECTION = b"------ SYSTEM PROPERTIES"
_DUMPSYS_SEPARATORS = {
    b"DUMP OF SERVICE accessibility:",
    b"DUMP OF SERVICE adb:",
    b"DUMP OF SERVICE appops:",
    b"DUMP OF SERVICE batterystats:",
    b"DUMP OF SERVICE dbinfo:",
    b"DUMP OF SERVICE package:",
    b"DUMP OF SERVICE platform_compat:",
}
_DUMPSTATE_DELIMITER = (
    b"------------------------------------------------------------------------------"
)
_GETPROP_LINE_RE = re.compile(rb"\[(.+?)\]: \[(.+?)\]")


class BugReportModule(MVTModule):
    """This class provides a base for all Android Bug Report modules."""

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

        self.zip_archive: Optional[ZipFile] = None
        self.extract_path: Optional[str] = None
        self.extract_files: List[str] = []
        self.zip_files: List[str] = []

    def from_dir(self, extract_path: str, extract_files: List[str]) -> None:
        self.extract_path = extract_path
        self.extract_files = extract_files

    def from_zip(self, zip_archive: Optional[ZipFile], zip_files: List[str]) -> None:
        self.zip_archive = zip_archive
        self.zip_files = zip_files

    def _get_files_by_pattern(self, pattern: str) -> list:
        file_names = []
        if self.zip_archive:
            for zip_file in self.zip_files:
                file_names.append(zip_file)
        else:
            file_names = self.extract_files

        return fnmatch.filter(file_names, pattern)

    def _get_files_by_patterns(self, patterns: list) -> list:
        for pattern in patterns:
            matches = self._get_files_by_pattern(pattern)
            if matches:
                return matches

        return []

    def _get_file_content(self, file_path: str) -> bytes:
        with self.resource_lock:
            if self.zip_archive:
                handle = self.zip_archive.open(file_path)
            else:
                if not self.extract_path:
                    raise ValueError("extract_path is not set")
                joined = os.path.join(self.extract_path, file_path)
                if (
                    not Path(joined)
                    .resolve()
                    .is_relative_to(Path(self.extract_path).resolve())
                ):
                    raise ValueError("unsafe file_path")
                handle = open(joined, "rb")

            data = handle.read()
            handle.close()

            return data

    def _get_dumpstate_file(self) -> Optional[bytes]:
        with self.resource_lock:
            if _DUMPSTATE_BYTES_CACHE_KEY in self.resource_cache:
                return self.resource_cache[_DUMPSTATE_BYTES_CACHE_KEY]

            content = None
            main = self._get_files_by_pattern("main_entry.txt")
            if main:
                main_content = self._get_file_content(main[0])
                try:
                    content = self._get_file_content(main_content.decode().strip())
                except KeyError:
                    pass
            else:
                dumpstate_logs = self._get_files_by_pattern("dumpState_*.log")
                if dumpstate_logs:
                    content = self._get_file_content(dumpstate_logs[0])
                else:
                    dumpsys_files = self._get_files_by_pattern("*/dumpsys.txt")
                    if dumpsys_files:
                        content = self._get_file_content(dumpsys_files[0])

            self.resource_cache[_DUMPSTATE_BYTES_CACHE_KEY] = content
            return content

    def _get_dumpstate_sections(self) -> dict[bytes, bytes]:
        with self.resource_lock:
            if _DUMPSTATE_SECTIONS_CACHE_KEY in self.resource_cache:
                return self.resource_cache[_DUMPSTATE_SECTIONS_CACHE_KEY]

            section_lines: dict[bytes, list[bytes]] = {
                separator: [] for separator in _DUMPSYS_SEPARATORS
            }
            section_lines[_SYSTEM_PROPERTIES_SECTION] = []
            current_section = None
            completed_sections = set()
            in_system_properties = False
            content = self._get_dumpstate_file()

            if content:
                for raw_line in io.BytesIO(content):
                    line = raw_line.rstrip(b"\r\n")
                    stripped = line.strip()

                    if stripped.startswith(_SYSTEM_PROPERTIES_SECTION):
                        in_system_properties = True
                    elif in_system_properties:
                        if stripped == b"------":
                            in_system_properties = False
                        elif _GETPROP_LINE_RE.search(line):
                            section_lines[_SYSTEM_PROPERTIES_SECTION].append(line)

                    if stripped in _DUMPSYS_SEPARATORS:
                        if current_section is not None:
                            completed_sections.add(current_section)
                        current_section = (
                            None if stripped in completed_sections else stripped
                        )
                        continue

                    if stripped.startswith(_DUMPSTATE_DELIMITER):
                        if current_section is not None:
                            completed_sections.add(current_section)
                        current_section = None
                        continue

                    if current_section is not None:
                        section_lines[current_section].append(line)

            sections = {
                separator: b"\n".join(lines)
                for separator, lines in section_lines.items()
            }
            self.resource_cache[_DUMPSTATE_SECTIONS_CACHE_KEY] = sections
            return sections

    def _get_dumpsys_section_bytes(self, separator: bytes) -> Optional[bytes]:
        sections = self._get_dumpstate_sections()
        if separator in sections:
            return sections[separator]

        content = self._get_dumpstate_file()
        if not content:
            return None
        return AndroidArtifact.extract_dumpsys_section(content, separator, binary=True)

    def _get_dumpsys_section(
        self, separator: str, errors: str = "replace"
    ) -> Optional[str]:
        cache_key = (
            "android_bugreport",
            "dumpstate",
            "section",
            separator,
            errors,
        )
        with self.resource_lock:
            if cache_key in self.resource_cache:
                return self.resource_cache[cache_key]

            section_bytes = self._get_dumpsys_section_bytes(separator.encode("utf-8"))
            section = (
                section_bytes.decode("utf-8", errors=errors)
                if section_bytes is not None
                else None
            )
            self.resource_cache[cache_key] = section
            return section

    def _get_system_properties_text(self, errors: str = "ignore") -> Optional[str]:
        cache_key = (
            "android_bugreport",
            "dumpstate",
            "system_properties",
            errors,
        )
        with self.resource_lock:
            if cache_key in self.resource_cache:
                return self.resource_cache[cache_key]

            sections = self._get_dumpstate_sections()
            section_bytes = sections.get(_SYSTEM_PROPERTIES_SECTION)
            section = (
                section_bytes.decode("utf-8", errors=errors)
                if section_bytes is not None
                else None
            )
            self.resource_cache[cache_key] = section
            return section

    def _get_file_modification_time(self, file_path: str) -> datetime.datetime:
        if self.zip_archive:
            with self.resource_lock:
                file_timetuple = self.zip_archive.getinfo(file_path).date_time
            return datetime.datetime(*file_timetuple)
        else:
            if not self.extract_path:
                raise ValueError("extract_path is not set")
            file_stat = os.stat(os.path.join(self.extract_path, file_path))
            return datetime.datetime.fromtimestamp(file_stat.st_mtime)
