# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from mvt.android.parsers.dumpsys import parse_dumpsys_packages

from ..utils import get_artifact


class TestDumpsysParsing:
    def test_packages_parsing(self):
        file = get_artifact("android_data/dumpsys_packages.txt")
        with open(file) as f:
            data = f.read()

        res = parse_dumpsys_packages(data)

        assert len(res) == 2
        assert res[0]["package_name"] == "com.samsung.android.provider.filterprovider"
        assert res[1]["package_name"] == "com.sec.android.app.DataCreate"
        assert len(res[0]["permissions"]) == 4
        assert len(res[0]["requested_permissions"]) == 0
        assert len(res[1]["permissions"]) == 34
        assert len(res[1]["requested_permissions"]) == 11
