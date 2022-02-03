# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os

import pkg_resources

from .base import AndroidExtraction

log = logging.getLogger(__name__)


class SELinuxStatus(AndroidExtraction):
    """This module checks if SELinux is being enforced."""

    slug = "selinux_status"

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 serial=None, fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

        self.results = {} if not results else results

    def run(self):
        self._adb_connect()
        output = self._adb_command("getenforce")
        self._adb_disconnect()

        status = output.lower().strip()
        self.results["status"] = status

        if status == "enforcing":
            self.log.info("SELinux is being regularly enforced")
        else:
            self.log.warning("SELinux status is \"%s\"!", status)
