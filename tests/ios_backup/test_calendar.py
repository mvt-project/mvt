# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os

from mvt.common.indicators import Indicators
from mvt.common.module import run_module
from mvt.ios.modules.mixed.calendar import Calendar

from ..utils import get_ios_backup_folder


class TestCalendarModule:
    def test_calendar(self):
        m = Calendar(target_path=get_ios_backup_folder())
        run_module(m)
        assert len(m.results) == 1
        assert len(m.timeline) == 4
        assert len(m.alertstore.alerts) == 0
        assert m.results[0]["summary"] == "Super interesting meeting"

    def test_calendar_with_explicit_file_path(self):
        backup_path = get_ios_backup_folder()
        database_path = os.path.join(
            backup_path, "20", "2041457d5fe04d39d0ab481178355df6781e6858"
        )
        m = Calendar(file_path=database_path)

        run_module(m)

        assert len(m.results) == 1
        assert m.results[0]["summary"] == "Super interesting meeting"

    def test_calendar_detection(self, indicator_file):
        m = Calendar(target_path=get_ios_backup_folder())
        ind = Indicators(log=logging.getLogger())
        ind.parse_stix2(indicator_file)
        ind.ioc_collections[0]["emails"].append("user@example.org")
        m.indicators = ind
        run_module(m)
        assert len(m.results) == 1
        assert len(m.timeline) == 4
        assert len(m.alertstore.alerts) == 1
