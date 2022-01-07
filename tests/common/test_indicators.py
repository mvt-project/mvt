import logging
import os

from mvt.common.indicators import Indicators

class TestIndicators:
    def test_parse_stix2(self, indicator_file):
        ind = Indicators(log=logging)
        ind.load_indicators_files([indicator_file], load_default=False)
        assert ind.ioc_count == 4
        assert len(ind.ioc_domains) == 1
        assert len(ind.ioc_emails) == 1
        assert len(ind.ioc_files) == 1
        assert len(ind.ioc_processes) == 1

    def test_check_domain(self, indicator_file):
        ind = Indicators(log=logging)
        ind.load_indicators_files([indicator_file], load_default=False)
        assert ind.check_domain("https://www.example.org/foobar")
        assert ind.check_domain("http://example.org:8080/toto")

    def test_env_stix(self, indicator_file):
        os.environ["MVT_STIX2"] = indicator_file
        ind = Indicators(log=logging)
        ind.load_indicators_files([indicator_file], load_default=False)
        assert ind.ioc_count == 4
