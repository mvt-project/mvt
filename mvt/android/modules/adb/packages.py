# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import List, Optional, Union

from rich.console import Console
from rich.progress import track
from rich.table import Table
from rich.text import Text

from mvt.android.parsers.dumpsys import parse_dumpsys_package_for_details
from mvt.common.virustotal import VTNoKey, VTQuotaExceeded, virustotal_lookup

from .base import AndroidExtraction

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
ROOT_PACKAGES: List[str] = [
    "com.noshufou.android.su",
    "com.noshufou.android.su.elite",
    "eu.chainfire.supersu",
    "com.koushikdutta.superuser",
    "com.thirdparty.superuser",
    "com.yellowes.su",
    "com.koushikdutta.rommanager",
    "com.koushikdutta.rommanager.license",
    "com.dimonvideo.luckypatcher",
    "com.chelpus.lackypatch",
    "com.ramdroid.appquarantine",
    "com.ramdroid.appquarantinepro",
    "com.devadvance.rootcloak",
    "com.devadvance.rootcloakplus",
    "de.robv.android.xposed.installer",
    "com.saurik.substrate",
    "com.zachspong.temprootremovejb",
    "com.amphoras.hidemyroot",
    "com.amphoras.hidemyrootadfree",
    "com.formyhm.hiderootPremium",
    "com.formyhm.hideroot",
    "me.phh.superuser",
    "eu.chainfire.supersu.pro",
    "com.kingouser.com",
    "com.topjohnwu.magisk",
]
SECURITY_PACKAGES = [
    "com.policydm",
    "com.samsung.android.app.omcagent",
    "com.samsung.android.securitylogagent",
    "com.sec.android.soagent",
]
SYSTEM_UPDATE_PACKAGES = [
    "com.android.updater",
    "com.google.android.gms",
    "com.huawei.android.hwouc",
    "com.lge.lgdmsclient",
    "com.motorola.ccc.ota",
    "com.oneplus.opbackup",
    "com.oppo.ota",
    "com.transsion.systemupdate",
    "com.wssyncmldm",
]


class Packages(AndroidExtraction):
    """This module extracts the list of installed packages."""

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        module_options: Optional[dict] = None,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[list] = None,
    ) -> None:
        super().__init__(
            file_path=file_path,
            target_path=target_path,
            results_path=results_path,
            module_options=module_options,
            log=log,
            results=results,
        )
        self._user_needed = False

    def serialize(self, record: dict) -> Union[dict, list]:
        records = []

        timestamps = [
            {"event": "package_install", "timestamp": record["timestamp"]},
            {
                "event": "package_first_install",
                "timestamp": record["first_install_time"],
            },
            {"event": "package_last_update", "timestamp": record["last_update_time"]},
        ]

        for timestamp in timestamps:
            records.append(
                {
                    "timestamp": timestamp["timestamp"],
                    "module": self.__class__.__name__,
                    "event": timestamp["event"],
                    "data": f"{record['package_name']} (system: {record['system']},"
                    f" third party: {record['third_party']})",
                }
            )

        return records

    def check_indicators(self) -> None:
        for result in self.results:
            if result["package_name"] in ROOT_PACKAGES:
                self.log.warning(
                    "Found an installed package related to "
                    'rooting/jailbreaking: "%s"',
                    result["package_name"],
                )
                self.detected.append(result)
                continue

            if result["package_name"] in SECURITY_PACKAGES and result["disabled"]:
                self.log.warning(
                    'Found a security package disabled: "%s"', result["package_name"]
                )

            if result["package_name"] in SYSTEM_UPDATE_PACKAGES and result["disabled"]:
                self.log.warning(
                    'System OTA update package "%s" disabled on the phone',
                    result["package_name"],
                )

            if not self.indicators:
                continue

            ioc = self.indicators.check_app_id(result.get("package_name"))
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)
                continue

            for package_file in result.get("files", []):
                ioc = self.indicators.check_file_hash(package_file["sha256"])
                if ioc:
                    result["matched_indicator"] = ioc
                    self.detected.append(result)

    @staticmethod
    def check_virustotal(packages: list) -> None:
        hashes = []
        for package in packages:
            for file in package.get("files", []):
                if file["sha256"] not in hashes:
                    hashes.append(file["sha256"])

        total_hashes = len(hashes)
        detections = {}

        progress_desc = f"Looking up {total_hashes} files..."
        for i in track(range(total_hashes), description=progress_desc):
            try:
                results = virustotal_lookup(hashes[i])
            except VTNoKey:
                return
            except VTQuotaExceeded as exc:
                print("Unable to continue: %s", exc)
                break

            if not results:
                continue

            positives = results["attributes"]["last_analysis_stats"]["malicious"]
            total = len(results["attributes"]["last_analysis_results"])

            detections[hashes[i]] = f"{positives}/{total}"

        table = Table(title="VirusTotal Packages Detections")
        table.add_column("Package name")
        table.add_column("File path")
        table.add_column("Detections")

        for package in packages:
            for file in package.get("files", []):
                row = [package["package_name"], file["path"]]

                if file["sha256"] in detections:
                    detection = detections[file["sha256"]]
                    positives = detection.split("/")[0]
                    if int(positives) > 0:
                        row.append(Text(detection, "red bold"))
                    else:
                        row.append(detection)
                else:
                    row.append("not found")

                table.add_row(*row)

        console = Console()
        console.print(table)

    @staticmethod
    def parse_package_for_details(output: str) -> dict:
        lines = []
        in_packages = False
        for line in output.splitlines():
            if in_packages:
                if line.strip() == "":
                    break
                lines.append(line)
            if line.strip() == "Packages:":
                in_packages = True

        return parse_dumpsys_package_for_details("\n".join(lines))

    def _get_files_for_package(self, package_name: str) -> list:
        command = f"pm path {package_name}"
        if self._user_needed:
            command += " --user 0"
        output = self._adb_command(command)
        output = output.strip().replace("package:", "")
        if not output:
            return []

        package_files = []
        for file_path in output.splitlines():
            file_path = file_path.strip()

            md5 = self._adb_command(f"md5sum {file_path}").split(" ", maxsplit=1)[0]
            sha1 = self._adb_command(f"sha1sum {file_path}").split(" ", maxsplit=1)[0]
            sha256 = self._adb_command(f"sha256sum {file_path}").split(" ", maxsplit=1)[
                0
            ]
            sha512 = self._adb_command(f"sha512sum {file_path}").split(" ", maxsplit=1)[
                0
            ]

            package_files.append(
                {
                    "path": file_path,
                    "md5": md5,
                    "sha1": sha1,
                    "sha256": sha256,
                    "sha512": sha512,
                }
            )

        return package_files

    def run(self) -> None:
        self._adb_connect()

        packages = self._adb_command("pm list packages -u -i -f")
        if "java.lang.SecurityException" in packages or packages.strip() == "":
            self._user_needed = True
            packages = self._adb_command("pm list packages -u -i -f --user 0")

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
            command = f"pm list packages {cmd['arg']}"
            if self._user_needed:
                command += " --user 0"
            output = self._adb_command(command)
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
                self.log.info(
                    'Third-party package "%s" requested %d '
                    "potentially dangerous permissions",
                    result["package_name"],
                    dangerous_permissions_count,
                )

        packages_to_lookup = []
        for result in self.results:
            if result["system"]:
                continue

            packages_to_lookup.append(result)
            self.log.info(
                'Found non-system package with name "%s" installed by "%s" on %s',
                result["package_name"],
                result["installer"],
                result["timestamp"],
            )

        if not self.module_options.get("fast_mode", None):
            self.check_virustotal(packages_to_lookup)

        self.log.info(
            "Extracted at total of %d installed package names", len(self.results)
        )

        self._adb_disconnect()
