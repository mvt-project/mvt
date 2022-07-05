# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import os
import platform

from mvt.common.utils import secure_delete


class Lockdown:

    def __init__(self, uuids: list = []) -> None:
        self.uuids = uuids
        self.lockdown_folder = self._get_lockdown_folder()

    @staticmethod
    def _get_lockdown_folder():
        system = platform.system()
        if system == "Linux":
            return "/var/lib/lockdown/"
        elif system == "Darwin":
            return "/var/db/lockdown/"
        elif system == "Windows":
            return os.path.join(os.environ.get("ALLUSERSPROFILE", ""),
                                "Apple", "Lockdown")

    @staticmethod
    def _get_pymobiledevice_folder():
        return os.path.expanduser("~/.pymobiledevice3")

    def delete_cert(self, cert_file) -> None:
        if not self.lockdown_folder:
            return

        cert_path = os.path.join(self.lockdown_folder, cert_file)
        if not os.path.exists(cert_path):
            return

        secure_delete(cert_path)

    def find_certs(self) -> list:
        if not self.lockdown_folder or not os.path.exists(self.lockdown_folder):
            return []

        lockdown_certs = []
        for file_name in os.listdir(self.lockdown_folder):
            if not file_name.endswith(".plist"):
                continue

            if file_name == "SystemConfiguration.plist":
                continue

            file_path = os.path.join(self.lockdown_folder, file_name)
            lockdown_certs.append(file_path)

        return sorted(lockdown_certs)
