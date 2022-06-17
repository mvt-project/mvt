# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from mvt.android.parsers.dumpsys import parse_dumpsys_appops

from ..utils import get_artifact


class TestDumpsysParsing:

    def test_appops_parsing(self):
        file = get_artifact("android_data/dumpsys_appops.txt")
        with open(file) as f:
            data = f.read()
        res = parse_dumpsys_appops(data)

        assert len(res) == 12
        assert res[0]["package_name"] == "com.android.phone"
        assert res[0]["uid"] == "0"
        assert len(res[0]["permissions"]) == 1
        assert res[0]["permissions"][0]["name"] == "MANAGE_IPSEC_TUNNELS"
        assert res[0]["permissions"][0]["access"] == "allow"
        assert res[6]["package_name"] == "com.sec.factory.camera"
        assert len(res[6]["permissions"][1]["entries"]) == 1
        assert len(res[11]["permissions"]) == 4
