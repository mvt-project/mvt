# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import json
import logging
import os

import pkg_resources
from tqdm import tqdm

from mvt.common.module import InsufficientPrivileges
from mvt.common.utils import get_sha256_from_file_path

from .modules.adb.base import AndroidExtraction

log = logging.getLogger(__name__)

# TODO: Would be better to replace tqdm with rich.progress to reduce
#       the number of dependencies. Need to investigate whether
#       it's possible to have a similar callback system.
class PullProgress(tqdm):
    """PullProgress is a tqdm update system for APK downloads."""

    def update_to(self, file_name, current, total):
        if total is not None:
            self.total = total
        self.update(current - self.n)


class Package:
    """Package indicates a package name and all the files associated with it."""

    def __init__(self, name, files=None):
        self.name = name
        self.files = files or []


class DownloadAPKs(AndroidExtraction):
    """DownloadAPKs is the main class operating the download of APKs
    from the device."""

    def __init__(self, output_folder=None, all_apks=False, packages=None):
        """Initialize module.
        :param output_folder: Path to the folder where data should be stored
        :param all_apks: Boolean indicating whether to download all packages
                         or filter known-goods
        :param packages: Provided list of packages, typically for JSON checks
        """
        super().__init__(file_path=None, base_folder=None,
                         output_folder=output_folder)

        self.output_folder_apk = None
        self.packages = packages or []
        self.all_apks = all_apks

        self._safe_packages = []

    @classmethod
    def from_json(cls, json_path):
        """Initialize this class from an existing apks.json file.
        :param json_path: Path to the apks.json file to parse.
        """
        with open(json_path, "r") as handle:
            data = json.load(handle)

            packages = []
            for entry in data:
                package = Package(entry["name"], entry["files"])
                packages.append(package)

            return cls(packages=packages)

    def _load_safe_packages(self):
        """Load known-good package names.
        """
        safe_packages_path = os.path.join("data", "safe_packages.txt")
        safe_packages_string = pkg_resources.resource_string(__name__, safe_packages_path)
        safe_packages_list = safe_packages_string.decode("utf-8").split("\n")
        self._safe_packages.extend(safe_packages_list)

    def _clean_output(self, output):
        """Clean adb shell command output.
        :param output: Command output to clean.
        """
        return output.strip().replace("package:", "")

    def get_packages(self):
        """Retrieve package names from the device using adb.
        """
        log.info("Retrieving package names ...")

        if not self.all_apks:
            self._load_safe_packages()

        output = self._adb_command("pm list packages")
        total = 0
        for line in output.split("\n"):
            package_name = self._clean_output(line)
            if package_name == "":
                continue

            total += 1

            if not self.all_apks and package_name in self._safe_packages:
                continue

            if package_name not in self.packages:
                self.packages.append(Package(package_name))

        log.info("There are %d packages installed on the device. I selected %d for inspection.",
                 total, len(self.packages))

    def pull_package_file(self, package_name, remote_path):
        """Pull files related to specific package from the device.
        :param package_name: Name of the package to download
        :param remote_path: Path to the file to download
        :returns: Path to the local copy
        """
        log.info("Downloading %s ...", remote_path)

        file_name = ""
        if "==/" in remote_path:
            file_name = "_" + remote_path.split("==/")[1].replace(".apk", "")

        local_path = os.path.join(self.output_folder_apk,
                                  f"{package_name}{file_name}.apk")
        name_counter = 0
        while True:
            if not os.path.exists(local_path):
                break

            name_counter += 1
            local_path = os.path.join(self.output_folder_apk,
                                      f"{package_name}{file_name}_{name_counter}.apk")

        try:
            with PullProgress(unit='B', unit_divisor=1024, unit_scale=True,
                              miniters=1) as pp:
                self._adb_download(remote_path, local_path,
                                   progress_callback=pp.update_to)
        except InsufficientPrivileges:
            log.warn("Unable to pull package file from %s: insufficient privileges, it might be a system app",
                     remote_path)
            self._adb_reconnect()
            return None
        except Exception as e:
            log.exception("Failed to pull package file from %s: %s",
                          remote_path, e)
            self._adb_reconnect()
            return None

        return local_path

    def pull_packages(self):
        """Download all files of all selected packages from the device.
        """
        log.info("Starting extraction of installed APKs at folder %s", self.output_folder)

        if not os.path.exists(self.output_folder):
            os.mkdir(self.output_folder)

        log.info("Downloading packages from device. This might take some time ...")

        self.output_folder_apk = os.path.join(self.output_folder, "apks")
        if not os.path.exists(self.output_folder_apk):
            os.mkdir(self.output_folder_apk)

        total_packages = len(self.packages)
        counter = 0
        for package in self.packages:
            counter += 1

            log.info("[%d/%d] Package: %s", counter, total_packages, package.name)

            try:
                output = self._adb_command(f"pm path {package.name}")
                output = self._clean_output(output)
                if not output:
                    continue
            except Exception as e:
                log.exception("Failed to get path of package %s: %s", package.name, e)
                self._adb_reconnect()
                continue

            # Sometimes the package path contains multiple lines for multiple apks.
            # We loop through each line and download each file.
            for path in output.split("\n"):
                device_path = path.strip()
                file_path = self.pull_package_file(package.name, device_path)
                if not file_path:
                    continue

                # We add the apk metadata to the package object.
                package.files.append({
                    "path": device_path,
                    "local_name": file_path,
                    "sha256": get_sha256_from_file_path(file_path),
                })

    def save_json(self):
        """Save the results to the package.json file.
        """
        json_path = os.path.join(self.output_folder, "apks.json")
        packages = []
        for package in self.packages:
            packages.append(package.__dict__)

        with open(json_path, "w") as handle:
            json.dump(packages, handle, indent=4)

    def run(self):
        """Run all steps of fetch-apk.
        """
        self._adb_connect()
        self.get_packages()
        self.pull_packages()
        self.save_json()
        self._adb_disconnect()
