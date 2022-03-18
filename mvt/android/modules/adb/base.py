# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import base64
import getpass
import logging
import os
import random
import string
import sys
import tempfile
import time

from adb_shell.adb_device import AdbDeviceTcp, AdbDeviceUsb
from adb_shell.auth.keygen import keygen, write_public_keyfile
from adb_shell.auth.sign_pythonrsa import PythonRSASigner
from adb_shell.exceptions import (AdbCommandFailureException, DeviceAuthError,
                                  UsbDeviceNotFoundError, UsbReadFailedError)
from usb1 import USBErrorAccess, USBErrorBusy

from mvt.android.parsers.backup import (InvalidBackupPassword, parse_ab_header,
                                        parse_backup_file)
from mvt.common.module import InsufficientPrivileges, MVTModule

log = logging.getLogger(__name__)

ADB_KEY_PATH = os.path.expanduser("~/.android/adbkey")
ADB_PUB_KEY_PATH = os.path.expanduser("~/.android/adbkey.pub")


class AndroidExtraction(MVTModule):
    """This class provides a base for all Android extraction modules."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

        self.device = None
        self.serial = None

    @staticmethod
    def _adb_check_keys():
        """Make sure Android adb keys exist."""
        if not os.path.isdir(os.path.dirname(ADB_KEY_PATH)):
            os.makedirs(os.path.dirname(ADB_KEY_PATH))

        if not os.path.exists(ADB_KEY_PATH):
            keygen(ADB_KEY_PATH)

        if not os.path.exists(ADB_PUB_KEY_PATH):
            write_public_keyfile(ADB_KEY_PATH, ADB_PUB_KEY_PATH)

    def _adb_connect(self):
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
                log.critical("No device found. Make sure it is connected and unlocked.")
                sys.exit(-1)
        # Otherwise we try to use the TCP transport.
        else:
            addr = self.serial.split(":")
            if len(addr) < 2:
                raise ValueError("TCP serial number must follow the format: `address:port`")

            self.device = AdbDeviceTcp(addr[0], int(addr[1]),
                                       default_transport_timeout_s=30.)

        while True:
            try:
                self.device.connect(rsa_keys=[signer], auth_timeout_s=5)
            except (USBErrorBusy, USBErrorAccess):
                log.critical("Device is busy, maybe run `adb kill-server` and try again.")
                sys.exit(-1)
            except DeviceAuthError:
                log.error("You need to authorize this computer on the Android device. Retrying in 5 seconds...")
                time.sleep(5)
            except UsbReadFailedError:
                log.error("Unable to connect to the device over USB. Try to unplug, plug the device and start again.")
                sys.exit(-1)
            except OSError as e:
                if e.errno == 113 and self.serial:
                    log.critical("Unable to connect to the device %s: did you specify the correct IP addres?",
                                 self.serial)
                    sys.exit(-1)
            else:
                break

    def _adb_disconnect(self):
        """Close adb connection to the device."""
        self.device.close()

    def _adb_reconnect(self):
        """Reconnect to device using adb."""
        log.info("Reconnecting ...")
        self._adb_disconnect()
        self._adb_connect()

    def _adb_command(self, command):
        """Execute an adb shell command.

        :param command: Shell command to execute
        :returns: Output of command

        """
        return self.device.shell(command, read_timeout_s=200.0)

    def _adb_check_if_root(self):
        """Check if we have a `su` binary on the Android device.


        :returns: Boolean indicating whether a `su` binary is present or not

        """
        return bool(self._adb_command("command -v su"))

    def _adb_root_or_die(self):
        """Check if we have a `su` binary, otherwise raise an Exception."""
        if not self._adb_check_if_root():
            raise InsufficientPrivileges("This module is optionally available in case the device is already rooted. Do NOT root your own device!")

    def _adb_command_as_root(self, command):
        """Execute an adb shell command.

        :param command: Shell command to execute as root
        :returns: Output of command

        """
        return self._adb_command(f"su -c {command}")

    def _adb_check_file_exists(self, file):
        """Verify that a file exists.

        :param file: Path of the file
        :returns: Boolean indicating whether the file exists or not

        """

        # TODO: Need to support checking files without root privileges as well.

        # Connect to the device over adb.
        self._adb_connect()
        # Check if we have root, if not raise an Exception.
        self._adb_root_or_die()

        return bool(self._adb_command_as_root(f"[ ! -f {file} ] || echo 1"))

    def _adb_download(self, remote_path, local_path, progress_callback=None, retry_root=True):
        """Download a file form the device.

        :param remote_path: Path to download from the device
        :param local_path: Path to where to locally store the copy of the file
        :param progress_callback: Callback for download progress bar (Default value = None)
        :param retry_root: Default value = True)

        """
        try:
            self.device.pull(remote_path, local_path, progress_callback)
        except AdbCommandFailureException as e:
            if retry_root:
                self._adb_download_root(remote_path, local_path, progress_callback)
            else:
                raise Exception(f"Unable to download file {remote_path}: {e}")

    def _adb_download_root(self, remote_path, local_path, progress_callback=None):
        try:
            # Check if we have root, if not raise an Exception.
            self._adb_root_or_die()

            # We generate a random temporary filename.
            tmp_filename = "tmp_" + ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=10))

            # We create a temporary local file.
            new_remote_path = f"/sdcard/{tmp_filename}"

            # We copy the file from the data folder to /sdcard/.
            cp = self._adb_command_as_root(f"cp {remote_path} {new_remote_path}")
            if cp.startswith("cp: ") and "No such file or directory" in cp:
                raise Exception(f"Unable to process file {remote_path}: File not found")
            elif cp.startswith("cp: ") and "Permission denied" in cp:
                raise Exception(f"Unable to process file {remote_path}: Permission denied")

            # We download from /sdcard/ to the local temporary file.
            # If it doesn't work now, don't try again (retry_root=False)
            self._adb_download(new_remote_path, local_path, retry_root=False)

            # Delete the copy on /sdcard/.
            self._adb_command(f"rm -rf {new_remote_path}")

        except AdbCommandFailureException as e:
            raise Exception(f"Unable to download file {remote_path}: {e}")

    def _adb_process_file(self, remote_path, process_routine):
        """Download a local copy of a file which is only accessible as root.
        This is a wrapper around process_routine.

        :param remote_path: Path of the file on the device to process
        :param process_routine: Function to be called on the local copy of the
                                downloaded file

        """
        # Connect to the device over adb.
        self._adb_connect()
        # Check if we have root, if not raise an Exception.
        self._adb_root_or_die()

        # We create a temporary local file.
        tmp = tempfile.NamedTemporaryFile()
        local_path = tmp.name
        local_name = os.path.basename(tmp.name)
        new_remote_path = f"/sdcard/Download/{local_name}"

        # We copy the file from the data folder to /sdcard/.
        cp = self._adb_command_as_root(f"cp {remote_path} {new_remote_path}")
        if cp.startswith("cp: ") and "No such file or directory" in cp:
            raise Exception(f"Unable to process file {remote_path}: File not found")
        elif cp.startswith("cp: ") and "Permission denied" in cp:
            raise Exception(f"Unable to process file {remote_path}: Permission denied")

        # We download from /sdcard/ to the local temporary file.
        self._adb_download(new_remote_path, local_path)

        # Launch the provided process routine!
        process_routine(local_path)

        # Delete the local copy.
        tmp.close()
        # Delete the copy on /sdcard/.
        self._adb_command(f"rm -f {new_remote_path}")
        # Disconnect from the device.
        self._adb_disconnect()

    def _generate_backup(self, package_name):
        self.log.warning("Please check phone and accept Android backup prompt. You may need to set a backup password. \a")

        # TODO: Base64 encoding as temporary fix to avoid byte-mangling over the shell transport...
        backup_output_b64 = self._adb_command("/system/bin/bu backup -nocompress '{}' | base64".format(
            package_name))
        backup_output = base64.b64decode(backup_output_b64)
        header = parse_ab_header(backup_output)

        if not header["backup"]:
            self.log.error("Extracting SMS via Android backup failed. No valid backup data found.")
            return

        if header["encryption"] == "none":
            return parse_backup_file(backup_output, password=None)

        for password_retry in range(0, 3):
            backup_password = getpass.getpass(prompt="Backup password: ", stream=None)
            try:
                decrypted_backup_tar = parse_backup_file(backup_output, backup_password)
                return decrypted_backup_tar
            except InvalidBackupPassword:
                self.log.error("You provided the wrong password! Please try again...")

        self.log.warn("All attempts to decrypt backup with password failed!")

    def run(self):
        """Run the main procedure."""
        raise NotImplementedError
