# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os

import pkg_resources

from .base import AndroidExtraction

log = logging.getLogger(__name__)

class Packages(AndroidExtraction):
    """This module extracts the list of installed packages."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 serial=None, fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record):
        records = []

        timestamps = [
            {"event": "package_install", "timestamp": record["timestamp"]},
            {"event": "package_first_install", "timestamp": record["first_install_time"]},
            {"event": "package_last_update", "timestamp": record["last_update_time"]},
        ]

        for ts in timestamps:
            records.append({
                "timestamp": ts["timestamp"],
                "module": self.__class__.__name__,
                "event": ts["event"],
                "data": f"{record['package_name']} (system: {record['system']}, third party: {record['third_party']})",
            })

        return records

    def check_indicators(self):
        root_packages_path = os.path.join("..", "..", "data", "root_packages.txt")
        root_packages_string = pkg_resources.resource_string(__name__, root_packages_path)
        root_packages = root_packages_string.decode("utf-8").split("\n")
        root_packages = [rp.strip() for rp in root_packages]


        for result in self.results:
            if result["package_name"] in root_packages:
                self.log.warning("Found an installed package related to rooting/jailbreaking: \"%s\"",
                                result["package_name"])
                self.detected.append(result)
            if result["package_name"] in self.indicators.ioc_app_ids:
                self.log.warning("Found a malicious package name: \"%s\"",
                                 result["package_name"])
                self.detected.append(result)
                for file in result["files"]:
                    if file["sha256"] in self.indicators.ioc_files_sha256:
                        self.log.warning("Found a malicious APK: \"%s\" %s",
                                         result["package_name"],
                                         file["sha256"])
                        self.detected.append(result)

    def _get_files_for_package(self, package_name):
        output = self._adb_command(f"pm path {package_name}")
        output = output.strip().replace("package:", "")
        if not output:
            return []

        package_files = []
        for file_path in output.split("\n"):
            file_path = file_path.strip()

            md5 = self._adb_command(f"md5sum {file_path}").split(" ")[0]
            sha1 = self._adb_command(f"sha1sum {file_path}").split(" ")[0]
            sha256 = self._adb_command(f"sha256sum {file_path}").split(" ")[0]
            sha512 = self._adb_command(f"sha512sum {file_path}").split(" ")[0]

            package_files.append({
                "path": file_path,
                "md5": md5,
                "sha1": sha1,
                "sha256": sha256,
                "sha512": sha512,
            })

        return package_files

    def run(self):
        self._adb_connect()

        packages = self._adb_command("pm list packages -U -u -i -f")
        for line in packages.split("\n"):
            line = line.strip()
            if not line.startswith("package:"):
                continue

            fields = line.split()
            file_name, package_name = fields[0].split(":")[1].rsplit("=", 1)

            try:
                installer = fields[1].split("=")[1].strip()
            except IndexError:
                installer = None
            else:
                if installer == "null":
                    installer = None

            try:
                uid = fields[2].split(":")[1].strip()
            except IndexError:
                uid = None

            dumpsys = self._adb_command(f"dumpsys package {package_name} | grep -A2 timeStamp").split("\n")
            timestamp = dumpsys[0].split("=")[1].strip()
            first_install = dumpsys[1].split("=")[1].strip()
            last_update = dumpsys[2].split("=")[1].strip()

            package_files = self._get_files_for_package(package_name)

            self.results.append({
                "package_name": package_name,
                "file_name": file_name,
                "installer": installer,
                "timestamp": timestamp,
                "first_install_time": first_install,
                "last_update_time": last_update,
                "uid": uid,
                "disabled": False,
                "system": False,
                "third_party": False,
                "files": package_files,
            })

        cmds = [
            {"field": "disabled", "arg": "-d"},
            {"field": "system", "arg": "-s"},
            {"field": "third_party", "arg": "-3"},
        ]
        for cmd in cmds:
            output = self._adb_command(f"pm list packages {cmd['arg']}")
            for line in output.split("\n"):
                line = line.strip()
                if not line.startswith("package:"):
                    continue

                package_name = line.split(":", 1)[1]
                for i, result in enumerate(self.results):
                    if result["package_name"] == package_name:
                        self.results[i][cmd["field"]] = True

        for result in self.results:
            if result["system"]:
                continue

            self.log.info("Found non-system package with name \"%s\" installed by \"%s\" on %s",
                          result["package_name"], result["installer"], result["timestamp"])

        self.log.info("Extracted at total of %d installed package names",
                      len(self.results))

        self._adb_disconnect()
