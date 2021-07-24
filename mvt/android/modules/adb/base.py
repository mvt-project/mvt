# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 MVT Project Developers.
# See the file 'LICENSE' for usage and copying permissions, or find a copy at
#   https://github.com/mvt-project/mvt/blob/main/LICENSE

import os
import random
import string
import sys
import time
import logging
import tempfile
from adb_shell.adb_device import AdbDeviceUsb
from adb_shell.auth.keygen import keygen, write_public_keyfile
from adb_shell.auth.sign_pythonrsa import PythonRSASigner
from adb_shell.exceptions import DeviceAuthError, AdbCommandFailureException
from usb1 import USBErrorBusy, USBErrorAccess

from mvt.common.module import MVTModule

log = logging.getLogger(__name__)

ADB_KEY_PATH = os.path.expanduser("~/.android/adbkey")
ADB_PUB_KEY_PATH = os.path.expanduser("~/.android/adbkey.pub")

class AndroidExtraction(MVTModule):
    """This class provides a base for all Android extraction modules."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        """Initialize Android extraction module.
        :param file_path: Path to the database file to parse
        :param base_folder: Path to a base folder containing an Android dump
        :param output_folder: Path to the folder where to store extraction
                              results
        """
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

        self.device = None

    def _adb_check_keys(self):
        """Make sure Android adb keys exist.
        """
        if not os.path.exists(ADB_KEY_PATH):
            keygen(ADB_KEY_PATH)

        if not os.path.exists(ADB_PUB_KEY_PATH):
            write_public_keyfile(ADB_KEY_PATH, ADB_PUB_KEY_PATH)

    def _adb_connect(self):
        """Connect to the device over adb.
        """
        self._adb_check_keys()

        with open(ADB_KEY_PATH, "rb") as handle:
            priv_key = handle.read()

        signer = PythonRSASigner("", priv_key)
        self.device = AdbDeviceUsb()

        while True:
            try:
                self.device.connect(rsa_keys=[signer], auth_timeout_s=5)
            except (USBErrorBusy, USBErrorAccess):
                log.critical("Device is busy, maybe run `adb kill-server` and try again.")
                sys.exit(-1)
            except DeviceAuthError:
                log.error("You need to authorize this computer on the Android device. Retrying in 5 seconds...")
                time.sleep(5)
            except Exception as e:
                log.critical(e)
                sys.exit(-1)
            else:
                break

    def _adb_disconnect(self):
        """Close adb connection to the device.
        """
        self.device.close()

    def _adb_reconnect(self):
        """Reconnect to device using adb.
        """
        log.info("Reconnecting ...")
        self._adb_disconnect()
        self._adb_connect()

    def _adb_command(self, command):
        """Execute an adb shell command.
        :param command: Shell command to execute
        :returns: Output of command
        """
        return self.device.shell(command)

    def _adb_check_if_root(self):
        """Check if we have a `su` binary on the Android device.
        :returns: Boolean indicating whether a `su` binary is present or not
        """
        return bool(self._adb_command("[ ! -f /sbin/su ] || echo 1"))

    def _adb_root_or_die(self):
        """Check if we have a `su` binary, otherwise raise an Exception.
        """
        if not self._adb_check_if_root():
            raise Exception("The Android device does not seem to have a `su` binary. Cannot run this module.")

    def _adb_command_as_root(self, command):
        """Execute an adb shell command.
        :param command: Shell command to execute as root
        :returns: Output of command
        """
        return self._adb_command(f"su -c {command}")

    def _adb_download(self, remote_path, local_path, progress_callback=None, retry_root=True):
        """Download a file form the device.
        :param remote_path: Path to download from the device
        :param local_path: Path to where to locally store the copy of the file
        :param progress_callback: Callback for download progress bar
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

    def run(self):
        """Run the main procedure.
        """
        raise NotImplementedError
