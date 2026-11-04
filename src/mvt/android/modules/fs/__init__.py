# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from mvt.common.module import MVTModule

from .browser_history import BrowserHistory

FS_MODULES: list[type[MVTModule]] = [BrowserHistory]
