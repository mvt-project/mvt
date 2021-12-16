import pytest
import logging
import os
from ..utils import get_artifact, init_setup
from mvt.common.indicators import Indicators, IndicatorsFileBadFormat


class TestIndicators:
    @pytest.fixture(scope="session", autouse=True)
    def set(self):
        init_setup()

    def test_parse_stix2(self):
        stix_path = get_artifact("test.stix2")
        ind = Indicators(log=logging)
        ind.parse_stix2(stix_path)
        assert ind.ioc_count == 4
        assert len(ind.ioc_domains) == 1
        assert len(ind.ioc_emails) == 1
        assert len(ind.ioc_files) == 1
        assert len(ind.ioc_processes) == 1

    def test_check_domain(self):
        ind = Indicators(log=logging)
        stix_path = get_artifact("test.stix2")
        ind.parse_stix2(stix_path)
        assert ind.check_domain("https://www.example.org/foobar") == True
        assert ind.check_domain("http://example.org:8080/toto") == True

    def test_env_stix(self):
        stix_path = get_artifact("test.stix2")
        os.environ["MVT_STIX2"] = stix_path
        ind = Indicators(log=logging)
        assert ind.ioc_count == 4
