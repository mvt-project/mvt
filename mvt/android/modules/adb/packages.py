# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os

import pkg_resources

from mvt.android.lookups.koodous import koodous_lookup
from mvt.android.lookups.virustotal import virustotal_lookup

from .base import AndroidExtraction

log = logging.getLogger(__name__)

DANGEROUS_PERMISSIONS_THRESHOLD = 10
DANGEROUS_PERMISSIONS = [
    "android.permission.ACCESS_COARSE_LOCATION",
    "android.permission.ACCESS_FINE_LOCATION",
    "android.permission.AUTHENTICATE_ACCOUNTS",
    "android.permission.CAMERA",
    "android.permission.DISABLE_KEYGUARD",
    "android.permission.PROCESS_OUTGOING_CALLS",
    "android.permission.READ_CALENDAR",
    "android.permission.READ_CALL_LOG",
    "android.permission.READ_CONTACTS",
    "android.permission.READ_PHONE_STATE",
    "android.permission.READ_SMS",
    "android.permission.RECEIVE_MMS",
    "android.permission.RECEIVE_SMS",
    "android.permission.RECEIVE_WAP_PUSH",
    "android.permission.RECORD_AUDIO",
    "android.permission.SEND_SMS",
    "android.permission.SYSTEM_ALERT_WINDOW",
    "android.permission.USE_CREDENTIALS",
    "android.permission.USE_SIP",
    "com.android.browser.permission.READ_HISTORY_BOOKMARKS",
]


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
        root_packages = root_packages_string.decode("utf-8").splitlines()
        root_packages = [rp.strip() for rp in root_packages]

        for result in self.results:
            if result["package_name"] in root_packages:
                self.log.warning("Found an installed package related to rooting/jailbreaking: \"%s\"",
                                 result["package_name"])
                self.detected.append(result)
                continue

            if not self.indicators:
                continue

            ioc = self.indicators.check_app_id(result.get("package_name"))
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)
                continue

            for package_file in result["files"]:
                ioc = self.indicators.check_file_hash(package_file["sha256"])
                if ioc:
                    result["matched_indicator"] = ioc
                    self.detected.append(result)

    @staticmethod
    def parse_package_for_details(output):
        details = {
            "uid": "",
            "version_name": "",
            "version_code": "",
            "timestamp": "",
            "first_install_time": "",
            "last_update_time": "",
            "requested_permissions": [],
        }

        in_permissions = False
        for line in output.splitlines():
            if in_permissions:
                if line.startswith(" " * 4) and not line.startswith(" " * 6):
                    in_permissions = False
                    continue

                permission = line.strip().split(":")[0]
                details["requested_permissions"].append(permission)

            if line.strip().startswith("userId="):
                details["uid"] = line.split("=")[1].strip()
            elif line.strip().startswith("versionName="):
                details["version_name"] = line.split("=")[1].strip()
            elif line.strip().startswith("versionCode="):
                details["version_code"] = line.split("=", 1)[1].strip()
            elif line.strip().startswith("timeStamp="):
                details["timestamp"] = line.split("=")[1].strip()
            elif line.strip().startswith("firstInstallTime="):
                details["first_install_time"] = line.split("=")[1].strip()
            elif line.strip().startswith("lastUpdateTime="):
                details["last_update_time"] = line.split("=")[1].strip()
            elif line.strip() == "requested permissions:":
                in_permissions = True
                continue

        return details

    def _get_files_for_package(self, package_name):
        output = self._adb_command(f"pm path {package_name}")
        output = output.strip().replace("package:", "")
        if not output:
            return []

        package_files = []
        for file_path in output.splitlines():
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

        packages = self._adb_command("pm list packages -u -i -f")

        for line in packages.splitlines():
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

            package_files = self._get_files_for_package(package_name)
            new_package = {
                "package_name": package_name,
                "file_name": file_name,
                "installer": installer,
                "disabled": False,
                "system": False,
                "third_party": False,
                "files": package_files,
            }

            dumpsys_package = self._adb_command(f"dumpsys package {package_name}")
            package_details = self.parse_package_for_details(dumpsys_package)
            new_package.update(package_details)

            self.results.append(new_package)

        cmds = [
            {"field": "disabled", "arg": "-d"},
            {"field": "system", "arg": "-s"},
            {"field": "third_party", "arg": "-3"},
        ]
        for cmd in cmds:
            output = self._adb_command(f"pm list packages {cmd['arg']}")
            for line in output.splitlines():
                line = line.strip()
                if not line.startswith("package:"):
                    continue

                package_name = line.split(":", 1)[1]
                for i, result in enumerate(self.results):
                    if result["package_name"] == package_name:
                        self.results[i][cmd["field"]] = True

        for result in self.results:
            if not result["third_party"]:
                continue

            dangerous_permissions_count = 0
            for perm in result["requested_permissions"]:
                if perm in DANGEROUS_PERMISSIONS:
                    dangerous_permissions_count += 1

            if dangerous_permissions_count >= DANGEROUS_PERMISSIONS_THRESHOLD:
                self.log.info("Third-party package \"%s\" requested %d potentially dangerous permissions",
                              result["package_name"], dangerous_permissions_count)

        packages_to_lookup = []
        for result in self.results:
            if result["system"]:
                continue

            packages_to_lookup.append(result)
            self.log.info("Found non-system package with name \"%s\" installed by \"%s\" on %s",
                          result["package_name"], result["installer"], result["timestamp"])

        if not self.fast_mode:
            virustotal_lookup(packages_to_lookup)
            koodous_lookup(packages_to_lookup)

        self.log.info("Extracted at total of %d installed package names",
                      len(self.results))

        self._adb_disconnect()
