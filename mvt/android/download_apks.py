# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import json
import logging
import os

from tqdm import tqdm

from mvt.common.module import InsufficientPrivileges

from .modules.adb.base import AndroidExtraction
from .modules.adb.packages import Packages

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


class DownloadAPKs(AndroidExtraction):
    """DownloadAPKs is the main class operating the download of APKs
    from the device.


    """

    def __init__(self, output_folder=None, all_apks=False, log=None,
                 packages=None):
        """Initialize module.
        :param output_folder: Path to the folder where data should be stored
        :param all_apks: Boolean indicating whether to download all packages
                         or filter known-goods
        :param packages: Provided list of packages, typically for JSON checks
        """
        super().__init__(output_folder=output_folder, log=log)

        self.packages = packages
        self.all_apks = all_apks
        self.output_folder_apk = None

    @classmethod
    def from_json(cls, json_path):
        """Initialize this class from an existing apks.json file.

        :param json_path: Path to the apks.json file to parse.

        """
        with open(json_path, "r", encoding="utf-8") as handle:
            packages = json.load(handle)
            return cls(packages=packages)

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

    def get_packages(self):
        """Use the Packages adb module to retrieve the list of packages.
        We reuse the same extraction logic to then download the APKs.


        """
        self.log.info("Retrieving list of installed packages...")

        m = Packages()
        m.log = self.log
        m.run()

        self.packages = m.results

    def pull_packages(self):
        """Download all files of all selected packages from the device."""
        log.info("Starting extraction of installed APKs at folder %s", self.output_folder)

        if not os.path.exists(self.output_folder):
            os.mkdir(self.output_folder)

        # If the user provided the flag --all-apks we select all packages.
        packages_selection = []
        if self.all_apks:
            log.info("Selected all %d available packages", len(self.packages))
            packages_selection = self.packages
        else:
            # Otherwise we loop through the packages and get only those that
            # are not marked as system.
            for package in self.packages:
                if not package.get("system", False):
                    packages_selection.append(package)

            log.info("Selected only %d packages which are not marked as system",
                     len(packages_selection))

        if len(packages_selection) == 0:
            log.info("No packages were selected for download")
            return

        log.info("Downloading packages from device. This might take some time ...")

        self.output_folder_apk = os.path.join(self.output_folder, "apks")
        if not os.path.exists(self.output_folder_apk):
            os.mkdir(self.output_folder_apk)

        counter = 0
        for package in packages_selection:
            counter += 1

            log.info("[%d/%d] Package: %s", counter, len(packages_selection),
                     package["package_name"])

            # Sometimes the package path contains multiple lines for multiple apks.
            # We loop through each line and download each file.
            for package_file in package["files"]:
                device_path = package_file["path"]
                local_path = self.pull_package_file(package["package_name"],
                                                    device_path)
                if not local_path:
                    continue

                package_file["local_path"] = local_path

        log.info("Download of selected packages completed")

    def save_json(self):
        """Save the results to the package.json file."""
        json_path = os.path.join(self.output_folder, "apks.json")
        with open(json_path, "w", encoding="utf-8") as handle:
            json.dump(self.packages, handle, indent=4)

    def run(self):
        """Run all steps of fetch-apk."""
        self.get_packages()
        self._adb_connect()
        self.pull_packages()
        self.save_json()
        self._adb_disconnect()
