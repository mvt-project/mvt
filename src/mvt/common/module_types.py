# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2025 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from .indicators import Indicator
from dataclasses import dataclass
from typing import List, Union, Optional


@dataclass
class ModuleAtomicResult:
    timestamp: Optional[str]
    matched_indicator: Optional[Indicator]


ModuleResults = List[ModuleAtomicResult]


@dataclass
class ModuleAtomicTimeline:
    timestamp: str
    module: str
    event: str
    data: str


ModuleTimeline = List[ModuleAtomicTimeline]
ModuleSerializedResult = Union[ModuleAtomicTimeline, ModuleTimeline]
