# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from mvt.android.parsers.dumpsys import (
    parse_dumpsys_battery_history,
    parse_dumpsys_packages,
)

from ..utils import get_artifact


class TestDumpsysParsing:
    def test_battery_history_parsing(self):
        file = get_artifact("android_data/dumpsys_battery.txt")
        with open(file) as f:
            data = f.read()

        res = parse_dumpsys_battery_history(data)

        assert len(res) == 5
        assert res[0]["package_name"] == "com.samsung.android.app.reminder"
        assert res[1]["event"] == "end_job"
        assert res[2]["event"] == "start_top"
        assert res[2]["uid"] == "u0a280"
        assert res[2]["package_name"] == "com.whatsapp"
        assert res[3]["event"] == "end_top"
        assert res[4]["package_name"] == "com.sec.android.app.launcher"

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
