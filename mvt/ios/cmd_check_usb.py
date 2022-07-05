# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import sys

from pymobiledevice3.exceptions import (ConnectionFailedError,
                                        FatalPairingError, NotTrustedError)
from pymobiledevice3.lockdown import LockdownClient

from mvt.common.command import Command

from .modules.usb import USB_MODULES

log = logging.getLogger(__name__)


class CmdIOSCheckUSB(Command):

    name = "check-usb"
    modules = USB_MODULES

    def __init__(self, target_path: str = None, results_path: str = None,
                 ioc_files: list = [], module_name: str = None, serial: str = None,
                 fast_mode: bool = False):
        super().__init__(target_path=target_path, results_path=results_path,
                         ioc_files=ioc_files, module_name=module_name,
                         serial=serial, fast_mode=fast_mode, log=log)
        self.lockdown = None

    def init(self):
        try:
            if self.serial:
                self.lockdown = LockdownClient(udid=self.serial)
            else:
                self.lockdown = LockdownClient()
        except NotTrustedError:
            log.error("Trust this computer from the prompt appearing on the iOS device and try again")
            sys.exit(-1)
        except (ConnectionRefusedError, ConnectionFailedError, FatalPairingError):
            log.error("Unable to connect to the device over USB: try to unplug, plug the device and start again")
            sys.exit(-1)

    def module_init(self, module):
        module.lockdown = self.lockdown
