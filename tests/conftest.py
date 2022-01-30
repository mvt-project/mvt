# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import os

import pytest

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
