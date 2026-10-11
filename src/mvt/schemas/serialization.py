# Mobile Verification Toolkit (MVT)
# Copyright (c) 2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

"""Validation and serialization helpers shared by all MVT output writers."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from mvt.common.utils import CustomJSONEncoder


def json_compatible(value: Any) -> Any:
    """Apply MVT's legacy conversions before validating JSON-native values."""

    return json.loads(json.dumps(value, cls=CustomJSONEncoder))


def validate_output(model: type[BaseModel], value: Any) -> Any:
    """Validate an output document and return JSON-serializable Python values."""

    compatible = json_compatible(value)
    return model.model_validate(compatible).model_dump(mode="json")


def write_output(path: str | Path, model: type[BaseModel], value: Any) -> None:
    """Validate and write an MVT JSON document."""

    validated = validate_output(model, value)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(validated, handle, indent=4)
