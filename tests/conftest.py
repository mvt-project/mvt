# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os

import pytest

from mvt.common.indicators import Indicators

from .artifacts.generate_stix import generate_test_stix_file


@pytest.fixture(scope="session", autouse=True)
def indicator_file(request, tmp_path_factory):
    indicator_dir = tmp_path_factory.mktemp("indicators")
    stix_path = indicator_dir / "indicators.stix2"
    generate_test_stix_file(stix_path)
    return str(stix_path)


@pytest.fixture(scope="session", autouse=True)
def clean_test_env(request, tmp_path_factory):
    try:
        del os.environ["MVT_STIX2"]
    except KeyError:
        pass


@pytest.fixture()
def indicators_factory(indicator_file):
    def f(
        domains=[],
        emails=[],
        file_names=[],
        processes=[],
        app_ids=[],
        app_cert_hashes=[],
        android_property_names=[],
        files_sha256=[],
    ):
        ind = Indicators(log=logging.getLogger())
        ind.parse_stix2(indicator_file)

        ind.ioc_collections[0]["domains"].extend(domains)
        ind.ioc_collections[0]["emails"].extend(emails)
        ind.ioc_collections[0]["file_names"].extend(file_names)
        ind.ioc_collections[0]["processes"].extend(processes)
        ind.ioc_collections[0]["app_ids"].extend(app_ids)
        ind.ioc_collections[0]["android_property_names"].extend(android_property_names)
        ind.ioc_collections[0]["files_sha256"].extend(files_sha256)
        ind.ioc_collections[0]["app_cert_hashes"].extend(app_cert_hashes)

        return ind

    return f
