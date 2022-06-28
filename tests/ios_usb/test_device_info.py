# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging

from mvt.common.module import run_module
from mvt.ios.modules.usb.device_info import DeviceInfo
from pymobiledevice3.lockdown import LockdownClient


class TestUSBDeviceInfo:
    def test_run(self, mocker):
        # Mock
        mocker.patch("pymobiledevice3.usbmux.select_device")
        mocker.patch("pymobiledevice3.service_connection.ServiceConnection.create")
        mocker.patch(
            "pymobiledevice3.lockdown.LockdownClient.query_type",
            return_value="com.apple.mobile.lockdown")
        mocker.patch(
            "pymobiledevice3.lockdown.LockdownClient.validate_pairing",
            return_value=True)
        mocker.patch(
            "pymobiledevice3.lockdown.LockdownClient.get_value",
            return_value={'DeviceClass': 'iPhone', 'ProductVersion': '14.3'}
        )

        lockdown = LockdownClient()

        m = DeviceInfo(log=logging)
        m.lockdown = lockdown
        run_module(m)
        assert len(m.results) == 2
