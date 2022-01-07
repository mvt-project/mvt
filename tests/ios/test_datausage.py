import logging

from mvt.common.indicators import Indicators
from mvt.ios.modules.mixed.net_datausage import Datausage
from mvt.common.module import run_module

from ..utils import get_backup_folder

class TestDatausageModule:
    def test_datausage(self):
        m = Datausage(base_folder=get_backup_folder(), log=logging, results=[])
        run_module(m)
        assert len(m.results) == 42
        assert len(m.timeline) == 60
        assert len(m.detected) == 0

    def test_detection(self, indicator_file):
        m = Datausage(base_folder=get_backup_folder(), log=logging, results=[])
        ind = Indicators(log=logging)
        ind.parse_stix2(indicator_file)
        # Adds a file that exists in the manifest
        ind.ioc_processes[0] = "CumulativeUsageTracker"
        m.indicators = ind
        run_module(m)
        assert len(m.detected) == 2
