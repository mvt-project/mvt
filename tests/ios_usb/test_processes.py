# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

from mvt.common.indicators import Indicators
from mvt.common.module import run_module
from mvt.ios.modules.usb.processes import Processes


class TestUSBProcesses:
    def test_run(self, mocker, indicator_file):
        mocker.patch("pymobiledevice3.services.base_service.BaseService.__init__")
        mocker.patch(
            "pymobiledevice3.services.os_trace.OsTraceService.get_pid_list",
            return_value={"Payload": {"1": {"ProcessName": "storebookkeeperd"}, "1854": {"ProcessName": "cfprefssd"}}}
        )

        ind = Indicators(log=logging)
        ind.parse_stix2(indicator_file)
        ind.ioc_collections[0]["processes"].append("cfprefssd")

        m = Processes(log=logging)
        m.indicators = ind
        run_module(m)
        assert len(m.results) == 2
        assert len(m.detected) == 1
