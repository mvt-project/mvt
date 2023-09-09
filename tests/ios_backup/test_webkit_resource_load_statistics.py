# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from mvt.common.module import run_module
from mvt.ios.modules.mixed.webkit_resource_load_statistics import (
    WebkitResourceLoadStatistics,
)

from ..utils import get_ios_backup_folder


class TestWebkitResourceLoadStatisticsModule:
    def test_webkit(self):
        m = WebkitResourceLoadStatistics(target_path=get_ios_backup_folder())
        m.is_backup = True
        run_module(m)
        assert len(m.results) == 2
        assert len(m.timeline) == 2
        assert len(m.detected) == 0
