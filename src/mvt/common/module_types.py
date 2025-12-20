# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2025 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from .indicators import Indicator

# ModuleAtomicResult is a flexible dictionary that can contain any data.
# Common fields include:
# - timestamp: Optional[str] - timestamp string
# - isodate: Optional[str] - ISO formatted date string
# - matched_indicator: Optional[Indicator] - indicator that matched this result
# - Any other module-specific fields
ModuleAtomicResult = Dict[str, Any]


ModuleResults = List[ModuleAtomicResult]


@dataclass
class ModuleAtomicTimeline:
    timestamp: str
    module: str
    event: str
    data: str


ModuleTimeline = List[ModuleAtomicTimeline]
# ModuleSerializedResult can be a proper timeline object or a plain dict for compatibility
ModuleSerializedResult = Union[
    ModuleAtomicTimeline, ModuleTimeline, Dict[str, Any], List[Dict[str, Any]]
]
