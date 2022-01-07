import pytest
import logging
import os

from mvt.common.indicators import Indicators

from ..utils import get_artifact, init_setup


class TestIndicators:
    @pytest.fixture(scope="session", autouse=True)
    def set(self):
        init_setup()

    def test_parse_stix2(self):
        stix_path = get_artifact("test.stix2")
        ind = Indicators(log=logging)
        ind.load_indicators_files([stix_path], load_default=False)
        assert ind.ioc_count == 4
        assert len(ind.ioc_domains) == 1
        assert len(ind.ioc_emails) == 1
        assert len(ind.ioc_files) == 1
        assert len(ind.ioc_processes) == 1

    def test_check_domain(self):
        ind = Indicators(log=logging)
        stix_path = get_artifact("test.stix2")
        ind.load_indicators_files([stix_path], load_default=False)
        assert ind.check_domain("https://www.example.org/foobar")
        assert ind.check_domain("http://example.org:8080/toto")

    def test_env_stix(self):
        stix_path = get_artifact("test.stix2")
        os.environ["MVT_STIX2"] = stix_path
        ind = Indicators(log=logging)
        ind.load_indicators_files([stix_path], load_default=False)
        assert ind.ioc_count == 4
