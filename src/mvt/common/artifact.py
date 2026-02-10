# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
from .module import MVTModule


class Artifact(MVTModule):
    """Base class for artifacts.

    XXX: Inheriting from MVTModule to have the same signature as other modules. Not sure if this is a good idea.
    """
