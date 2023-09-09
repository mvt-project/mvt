# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
import logging

from mvt.android.artifacts.dumpsys_dbinfo import DumpsysDBInfoArtifact
from mvt.common.indicators import Indicators

from ..utils import get_artifact


class TestDumpsysDBinfoArtifact:
    def test_parsing(self):
        dbi = DumpsysDBInfoArtifact()
        file = get_artifact("android_data/dumpsys_dbinfo.txt")
        with open(file) as f:
            data = f.read()

        assert len(dbi.results) == 0
        dbi.parse(data)
        assert len(dbi.results) == 5
        assert dbi.results[0]["action"] == "executeForCursorWindow"
        assert dbi.results[0]["sql"] == "PRAGMA database_list;"
        assert (
            dbi.results[0]["path"] == "/data/user/0/com.wssyncmldm/databases/idmsdk.db"
        )

    def test_ioc_check(self, indicator_file):
        dbi = DumpsysDBInfoArtifact()
        file = get_artifact("android_data/dumpsys_dbinfo.txt")
        with open(file) as f:
            data = f.read()
        dbi.parse(data)

        ind = Indicators(log=logging.getLogger())
        ind.parse_stix2(indicator_file)
        ind.ioc_collections[0]["app_ids"].append("com.wssyncmldm")
        dbi.indicators = ind
        assert len(dbi.detected) == 0
        dbi.check_indicators()
        assert len(dbi.detected) == 5
