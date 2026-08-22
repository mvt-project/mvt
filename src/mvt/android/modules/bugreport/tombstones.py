# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional

from mvt.android.artifacts.tombstone_crashes import TombstoneCrashArtifact
from mvt.common.module_types import ModuleResults
from .base import BugReportModule


class Tombstones(TombstoneCrashArtifact, BugReportModule):
    """This module extracts records from battery daily updates."""

    slug = "tombstones"

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
        tombstone_files = self._get_files_by_pattern("*/tombstone_*")
        if not tombstone_files:
            self.log.error(
                "Unable to find any tombstone files. "
                "Did you provide a valid bugreport archive?"
            )
            return

        grouped: dict[str, dict[str, str]] = {}
        for file_path in tombstone_files:
            file_name = file_path.rsplit("/", 1)[-1]
            source = "protobuf" if file_name.endswith(".pb") else "text"
            crash_id = file_name.removesuffix(".pb")
            grouped.setdefault(crash_id, {})[source] = file_path

        for crash_id, paths in sorted(grouped.items()):
            parsed_sources: dict[str, dict] = {}
            source_records: dict[str, dict] = {}
            for source in ("text", "protobuf"):
                file_path = paths.get(source)
                if file_path is None:
                    continue
                file_name = file_path.rsplit("/", 1)[-1]
                file_timestamp = self._get_file_modification_time(file_path)
                source_info = {
                    "file_name": file_name,
                    "file_timestamp": file_timestamp.isoformat(),
                    "parsed": False,
                    "error": None,
                    "record": None,
                }
                try:
                    data = self._get_file_content(file_path)
                    if source == "protobuf":
                        record = self.parse_protobuf_record(
                            file_name, file_timestamp, data
                        )
                    else:
                        record = self.parse_text_record(file_name, file_timestamp, data)
                    source_info["parsed"] = True
                    source_info["record"] = record
                    source_records[source] = record
                except Exception as exc:
                    source_info["error"] = str(exc)
                    self.log.error(
                        "Error parsing tombstone file %s: %s", file_path, exc
                    )
                parsed_sources[source] = source_info

            if not source_records:
                continue
            preferred = source_records.get("protobuf") or source_records["text"]
            canonical = dict(preferred)
            text_record = source_records.get("text")
            if text_record:
                for key, value in text_record.items():
                    if canonical.get(key) in (None, "", [], {}):
                        canonical[key] = value

            differences = {}
            protobuf_record = source_records.get("protobuf")
            if text_record and protobuf_record:
                for key in text_record.keys() & protobuf_record.keys():
                    if key in ("file_name", "file_timestamp"):
                        continue
                    if text_record[key] != protobuf_record[key]:
                        differences[key] = {
                            "text": text_record[key],
                            "protobuf": protobuf_record[key],
                        }
            canonical.update(
                {
                    "crash_id": crash_id,
                    "sources": parsed_sources,
                    "differences": differences,
                }
            )
            self.results.append(canonical)

        self.log.info(
            "Extracted a total of %d tombstone files",
            len(self.results),
        )
