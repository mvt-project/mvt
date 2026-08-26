# Mobile Verification Toolkit (MVT)
# Copyright (c) 2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

"""Public Pydantic models for files written by MVT.

Module records intentionally remain extensible: each extraction module has its own
record fields, while the root models make the top-level output shape predictable.
More specific modules can replace :class:`ModuleRecord` with a dedicated model.
"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, JsonValue, RootModel

OUTPUT_SCHEMA_VERSION: Literal["1.0"] = "1.0"
OutputModel = type[BaseModel]


class MVTOutputModel(BaseModel):
    """Base for stable output objects with no undocumented fields."""

    model_config = ConfigDict(extra="forbid", strict=True)


class ModuleRecord(BaseModel):
    """A JSON object produced by an extraction module.

    Module-specific keys are retained and represented in JSON Schema through
    ``additionalProperties``. Dedicated module models can provide stronger field
    contracts without changing the serialization machinery.
    """

    model_config = ConfigDict(extra="allow", strict=True)


class RecordListOutput(RootModel[list[ModuleRecord]]):
    """The standard output shape for built-in extraction modules."""


class MappingOutput(RootModel[dict[str, JsonValue]]):
    """Output shape for modules grouped by a dynamic string key."""


class GenericModuleOutput(RootModel[list[JsonValue] | dict[str, JsonValue]]):
    """Compatibility output shape for third-party modules without a model."""


class FileHash(MVTOutputModel):
    file_path: str
    sha256: str


class RunInfo(MVTOutputModel):
    target_path: Optional[str]
    mvt_version: str
    date: str
    ioc_files: list[str]
    hashes: list[FileHash]
    output_schema_version: Literal["1.0"]


class URLResult(MVTOutputModel):
    url: str
    expanded_url: Optional[str]
    timestamp: Optional[str]
    source: str


class URLResults(RootModel[list[URLResult]]):
    pass


AlertLevelName = Literal["INFORMATIONAL", "LOW", "MEDIUM", "HIGH", "CRITICAL"]


class AlertResult(MVTOutputModel):
    level: AlertLevelName
    module: str
    message: str
    event_time: str
    event: dict[str, JsonValue]
    matched_indicator: Optional[JsonValue] = None


class AlertResults(RootModel[list[AlertResult]]):
    pass


class TimelineEvent(MVTOutputModel):
    """Public contract for the records used to create ``timeline.csv``."""

    timestamp: Optional[str]
    module: str
    event: str
    data: str


class TimelineResults(RootModel[list[TimelineEvent]]):
    pass
