# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import base64
import logging
import os
import random
import string
import sys
import tempfile
import time
from typing import Callable, Optional

from adb_shell.adb_device import AdbDeviceTcp, AdbDeviceUsb
from adb_shell.auth.keygen import keygen, write_public_keyfile
from adb_shell.auth.sign_pythonrsa import PythonRSASigner
from adb_shell.exceptions import (
    AdbCommandFailureException,
    DeviceAuthError,
    UsbDeviceNotFoundError,
    UsbReadFailedError,
)
from usb1 import USBErrorAccess, USBErrorBusy

from mvt.android.modules.backup.helpers import prompt_or_load_android_backup_password
from mvt.android.parsers.backup import (
    InvalidBackupPassword,
    parse_ab_header,
    parse_backup_file,
)
from mvt.common.module import InsufficientPrivileges, MVTModule

ADB_KEY_PATH = os.path.expanduser("~/.android/adbkey")
ADB_PUB_KEY_PATH = os.path.expanduser("~/.android/adbkey.pub")


class AndroidExtraction(MVTModule):
    """This class provides a base for all Android extraction modules."""

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

        self.device = None
        self.serial = None

    @staticmethod
    def _adb_check_keys() -> None:
        """Make sure Android adb keys exist."""
        if not os.path.isdir(os.path.dirname(ADB_KEY_PATH)):
            os.makedirs(os.path.dirname(ADB_KEY_PATH))

        if not os.path.exists(ADB_KEY_PATH):
            keygen(ADB_KEY_PATH)

        if not os.path.exists(ADB_PUB_KEY_PATH):
            write_public_keyfile(ADB_KEY_PATH, ADB_PUB_KEY_PATH)

    def _adb_connect(self) -> None:
        """Connect to the device over adb."""
        self._adb_check_keys()

        with open(ADB_KEY_PATH, "rb") as handle:
            priv_key = handle.read()

        with open(ADB_PUB_KEY_PATH, "rb") as handle:
            pub_key = handle.read()

        signer = PythonRSASigner(pub_key, priv_key)

        # If no serial was specified or if the serial does not seem to be
        # a HOST:PORT definition, we use the USB transport.
        if not self.serial or ":" not in self.serial:
            try:
                self.device = AdbDeviceUsb(serial=self.serial)
            except UsbDeviceNotFoundError:
                self.log.critical(
                    "No device found. Make sure it is connected and unlocked."
                )
                sys.exit(-1)
        # Otherwise we try to use the TCP transport.
        else:
            addr = self.serial.split(":")
            if len(addr) < 2:
                raise ValueError(
                    "TCP serial number must follow the format: `address:port`"
                )

            self.device = AdbDeviceTcp(
                addr[0], int(addr[1]), default_transport_timeout_s=30.0
            )

        while True:
            try:
                self.device.connect(rsa_keys=[signer], auth_timeout_s=5)
            except (USBErrorBusy, USBErrorAccess):
                self.log.critical(
                    "Device is busy, maybe run `adb kill-server` and try again."
                )
                sys.exit(-1)
            except DeviceAuthError:
                self.log.error(
                    "You need to authorize this computer on the Android device. "
                    "Retrying in 5 seconds..."
                )
                time.sleep(5)
            except UsbReadFailedError:
                self.log.error(
                    "Unable to connect to the device over USB. "
                    "Try to unplug, plug the device and start again."
                )
                sys.exit(-1)
            except OSError as exc:
                if exc.errno == 113 and self.serial:
                    self.log.critical(
                        "Unable to connect to the device %s: "
                        "did you specify the correct IP address?",
                        self.serial,
                    )
                    sys.exit(-1)
            else:
                break

    def _adb_disconnect(self) -> None:
        """Close adb connection to the device."""
        self.device.close()

    def _adb_reconnect(self) -> None:
        """Reconnect to device using adb."""
        self.log.info("Reconnecting ...")
        self._adb_disconnect()
        self._adb_connect()

    def _adb_command(self, command: str) -> str:
        """Execute an adb shell command.

        :param command: Shell command to execute
        :returns: Output of command

        """
        return self.device.shell(command, read_timeout_s=200.0)

    def _adb_check_if_root(self) -> bool:
        """Check if we have a `su` binary on the Android device.


        :returns: Boolean indicating whether a `su` binary is present or not

        """
        result = self._adb_command("command -v su && su -c true")
        return bool(result) and "Permission denied" not in result

    def _adb_root_or_die(self) -> None:
        """Check if we have a `su` binary, otherwise raise an Exception."""
        if not self._adb_check_if_root():
            raise InsufficientPrivileges(
                "This module is optionally available "
                "in case the device is already rooted."
                " Do NOT root your own device!"
            )

    def _adb_command_as_root(self, command):
        """Execute an adb shell command.

        :param command: Shell command to execute as root
        :returns: Output of command

        """
        return self._adb_command(f"su -c {command}")

    def _adb_check_file_exists(self, file: str) -> bool:
        """Verify that a file exists.

        :param file: Path of the file
        :returns: Boolean indicating whether the file exists or not

        """

        # TODO: Need to support checking files without root privileges as well.

        # Check if we have root, if not raise an Exception.
        self._adb_root_or_die()

        return bool(self._adb_command_as_root(f"[ ! -f {file} ] || echo 1"))

    def _adb_download(
        self,
        remote_path: str,
        local_path: str,
        progress_callback: Optional[Callable] = None,
        retry_root: Optional[bool] = True,
    ) -> None:
        """Download a file form the device.

        :param remote_path: Path to download from the device
        :param local_path: Path to where to locally store the copy of the file
        :param progress_callback: Callback for download progress bar
                                  (Default value = None)
        :param retry_root: Default value = True)

        """
        try:
            self.device.pull(remote_path, local_path, progress_callback)
        except AdbCommandFailureException as exc:
            if retry_root:
                self._adb_download_root(remote_path, local_path, progress_callback)
            else:
                raise Exception(
                    f"Unable to download file {remote_path}: {exc}"
                ) from exc

    def _adb_download_root(
        self,
        remote_path: str,
        local_path: str,
        progress_callback: Optional[Callable] = None,
    ) -> None:
        try:
            # Check if we have root, if not raise an Exception.
            self._adb_root_or_die()

            # We generate a random temporary filename.
            allowed_chars = (
                string.ascii_uppercase + string.ascii_lowercase + string.digits
            )
            tmp_filename = "tmp_" + "".join(random.choices(allowed_chars, k=10))

            # We create a temporary local file.
            new_remote_path = f"/sdcard/{tmp_filename}"

            # We copy the file from the data folder to /sdcard/.
            cp_output = self._adb_command_as_root(f"cp {remote_path} {new_remote_path}")
            if (
                cp_output.startswith("cp: ")
                and "No such file or directory" in cp_output
            ):
                raise Exception(f"Unable to process file {remote_path}: File not found")
            if cp_output.startswith("cp: ") and "Permission denied" in cp_output:
                raise Exception(
                    f"Unable to process file {remote_path}: Permission denied"
                )

            # We download from /sdcard/ to the local temporary file.
            # If it doesn't work now, don't try again (retry_root=False)
            self._adb_download(
                new_remote_path, local_path, progress_callback, retry_root=False
            )

            # Delete the copy on /sdcard/.
            self._adb_command(f"rm -rf {new_remote_path}")

        except AdbCommandFailureException as exc:
            raise Exception(f"Unable to download file {remote_path}: {exc}") from exc

    def _adb_process_file(self, remote_path: str, process_routine: Callable) -> None:
        """Download a local copy of a file which is only accessible as root.
        This is a wrapper around process_routine.

        :param remote_path: Path of the file on the device to process
        :param process_routine: Function to be called on the local copy of the
                                downloaded file

        """
        # Connect to the device over adb.
        # Check if we have root, if not raise an Exception.
        self._adb_root_or_die()

        # We create a temporary local file.
        tmp = tempfile.NamedTemporaryFile()
        local_path = tmp.name
        local_name = os.path.basename(tmp.name)
        new_remote_path = f"/sdcard/Download/{local_name}"

        # We copy the file from the data folder to /sdcard/.
        cp_output = self._adb_command_as_root(f"cp {remote_path} {new_remote_path}")
        if cp_output.startswith("cp: ") and "No such file or directory" in cp_output:
            raise Exception(f"Unable to process file {remote_path}: File not found")
        if cp_output.startswith("cp: ") and "Permission denied" in cp_output:
            raise Exception(f"Unable to process file {remote_path}: Permission denied")

        # We download from /sdcard/ to the local temporary file.
        self._adb_download(new_remote_path, local_path)

        # Launch the provided process routine!
        process_routine(local_path)

        # Delete the local copy.
        tmp.close()
        # Delete the copy on /sdcard/.
        self._adb_command(f"rm -f {new_remote_path}")

    def _generate_backup(self, package_name: str) -> bytes:
        self.log.info(
            "Please check phone and accept Android backup prompt. "
            "You may need to set a backup password. \a"
        )

        if self.module_options.get("backup_password", None):
            self.log.warning(
                "Backup password already set from command line or environment "
                "variable. You should use the same password if enabling encryption!"
            )

        # TODO: Base64 encoding as temporary fix to avoid byte-mangling over
        #       the shell transport...
        cmd = f"/system/bin/bu backup -nocompress '{package_name}' | base64"
        backup_output_b64 = self._adb_command(cmd)
        backup_output = base64.b64decode(backup_output_b64)
        header = parse_ab_header(backup_output)

        if not header["backup"]:
            self.log.error(
                "Extracting SMS via Android backup failed. "
                "No valid backup data found."
            )
            return None

        if header["encryption"] == "none":
            return parse_backup_file(backup_output, password=None)

        for _ in range(0, 3):
            backup_password = prompt_or_load_android_backup_password(
                self.log, self.module_options
            )
            if not backup_password:
                # Fail as no backup password loaded for this encrypted backup
                self.log.critical("No backup password provided.")
            try:
                decrypted_backup_tar = parse_backup_file(backup_output, backup_password)
                return decrypted_backup_tar
            except InvalidBackupPassword:
                self.log.error("You provided the wrong password! Please try again...")

        self.log.error("All attempts to decrypt backup with password failed!")

        return None

    def run(self) -> None:
        """Run the main procedure."""
        raise NotImplementedError
