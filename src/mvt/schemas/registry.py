# Mobile Verification Toolkit (MVT)
# Copyright (c) 2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

"""Discovery and JSON Schema export for MVT output models."""

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable

from pydantic import BaseModel

from .models import (
    OUTPUT_SCHEMA_VERSION,
    AlertResults,
    RunInfo,
    TimelineResults,
    URLResults,
)

if TYPE_CHECKING:
    from mvt.common.module import MVTModule

COMMON_OUTPUT_MODELS: dict[str, type[BaseModel]] = {
    "alerts": AlertResults,
    "info": RunInfo,
    "timeline": TimelineResults,
    "urls": URLResults,
}

JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"


def _module_classes(platform: str) -> Iterable[type["MVTModule"]]:
    if platform == "ios":
        from mvt.ios.modules.backup import BACKUP_MODULES as IOS_BACKUP_MODULES
        from mvt.ios.modules.fs import FS_MODULES
        from mvt.ios.modules.mixed import MIXED_MODULES

        return IOS_BACKUP_MODULES + FS_MODULES + MIXED_MODULES
    if platform == "android":
        from mvt.android.modules.androidqf import ANDROIDQF_MODULES
        from mvt.android.modules.backup import BACKUP_MODULES as ANDROID_BACKUP_MODULES
        from mvt.android.modules.bugreport import BUGREPORT_MODULES
        from mvt.android.modules.intrusion_logs import INTRUSION_LOGS_MODULES

        return (
            ANDROID_BACKUP_MODULES
            + BUGREPORT_MODULES
            + ANDROIDQF_MODULES
            + INTRUSION_LOGS_MODULES
        )
    raise ValueError(f"Unsupported MVT platform: {platform}")


def get_output_models(platform: str) -> dict[str, type[BaseModel]]:
    """Return common and module output models available for a platform."""

    models = dict(COMMON_OUTPUT_MODELS)
    for module in _module_classes(platform):
        models[module.get_slug()] = module.output_model
    return dict(sorted(models.items()))


def get_output_model(name: str, platform: str | None = None) -> type[BaseModel]:
    """Look up an output model by file stem/module slug.

    ``platform`` is optional for common outputs. It is required when an output
    slug exists on both platforms and resolves to different models.
    """

    normalized = name.removesuffix(".json")
    if normalized.endswith("_detected"):
        return AlertResults
    if normalized in COMMON_OUTPUT_MODELS:
        return COMMON_OUTPUT_MODELS[normalized]
    if platform:
        try:
            return get_output_models(platform)[normalized]
        except KeyError as exc:
            raise KeyError(f"Unknown {platform} output schema: {name}") from exc

    matches = {
        models[normalized]
        for candidate in ("ios", "android")
        if normalized in (models := get_output_models(candidate))
    }
    if len(matches) == 1:
        return matches.pop()
    if len(matches) > 1:
        raise KeyError(f"Output schema {name!r} is ambiguous; specify a platform")
    raise KeyError(f"Unknown MVT output schema: {name}")


def schema_bundle(platform: str) -> dict[str, Any]:
    """Build a versioned bundle of Draft 2020-12 JSON Schemas."""

    return {
        "output_schema_version": OUTPUT_SCHEMA_VERSION,
        "platform": platform,
        "schemas": {
            name: _output_json_schema(name, model, platform)
            for name, model in get_output_models(platform).items()
        },
    }


def _output_json_schema(
    name: str, model: type[BaseModel], platform: str
) -> dict[str, Any]:
    schema = model.model_json_schema()
    return {
        "$schema": JSON_SCHEMA_DIALECT,
        "$id": f"urn:mvt:output-schema:{OUTPUT_SCHEMA_VERSION}:{platform}:{name}",
        **schema,
    }


def export_json_schemas(destination: str | os.PathLike[str], platform: str) -> list[Path]:
    """Write one JSON Schema per output and return the paths created."""

    destination_path = Path(destination)
    destination_path.mkdir(parents=True, exist_ok=True)
    written = []
    for name, model in get_output_models(platform).items():
        output_path = destination_path / f"{name}.schema.json"
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(_output_json_schema(name, model, platform), handle, indent=2)
            handle.write("\n")
        written.append(output_path)
    return written
