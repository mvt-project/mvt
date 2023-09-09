# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
import logging

from mvt.android.artifacts.processes import Processes
from mvt.common.indicators import Indicators

from ..utils import get_artifact


class TestProcessesArtifact:
    def test_parsing(self):
        p = Processes()
        file = get_artifact("android_data/ps.txt")
        with open(file) as f:
            data = f.read()

        assert len(p.results) == 0
        p.parse(data)
        assert len(p.results) == 17
        assert p.results[0]["proc_name"] == "init"

    def test_ioc_check(self, indicator_file):
        p = Processes()
        file = get_artifact("android_data/ps.txt")
        with open(file) as f:
            data = f.read()
        p.parse(data)

        ind = Indicators(log=logging.getLogger())
        ind.parse_stix2(indicator_file)
        ind.ioc_collections[0]["processes"].append("lru-add-drain")
        p.indicators = ind
        assert len(p.detected) == 0
        p.check_indicators()
        assert len(p.detected) == 1
