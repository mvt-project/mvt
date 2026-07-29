# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import datetime
import gzip
import io
import os
import re
from typing import IO, Optional

from mvt.android.artifacts.dumpsys_adb import DumpsysADBArtifact
from mvt.common.module_types import ModuleAtomicResult, ModuleSerializedResult
from mvt.common.utils import convert_datetime_to_iso

from .base import AndroidQFModule


ADB_STATES = {
    0: "unknown",
    1: "awaiting_user_approval",
    2: "user_allowed",
    3: "user_denied",
    4: "automatically_allowed",
    5: "denied_invalid_key",
    6: "denied_vold_decrypt",
    7: "disconnected",
}

LOG_LINE_RE = re.compile(
    r"^(?P<timestamp>\d{2}-\d{2}-\d{2} "
    r"\(GMT[+-]\d{2}:\d{2}\) \d{2}:\d{2}:\d{2}\.\d{3}) "
    r"\d+ [VDIWEAF] (?P<tag>[^:]+): (?P<message>.*)$"
)
ADB_KEY_RE = re.compile(
    r"^Logging key (?P<key>.*), state = (?P<state>\d+), "
    r"alwaysAllow = (?P<always_allow>true|false), "
    r"lastConnectionTime = (?P<last_connection_time>\d+), "
    r"authWindow = (?P<auth_window>\d+)$"
)
USB_DEVICE_RE = re.compile(
    r"^USB device attached: vidpid (?P<vendor_id>[^:\s]+):(?P<product_id>\S+) "
    r"mfg/product/ver(?:/serial)? "
    r"(?P<manufacturer>.*?)/(?P<product>.*?)/(?P<version>.*?)/(?P<serial>.*?) "
    r"hasAudio/HID/Storage: "
    r"(?P<has_audio>true|false)/(?P<has_hid>true|false)/"
    r"(?P<has_storage>true|false)$"
)
USB_UEVENT_RE = re.compile(r"^USB UEVENT: \{(?P<properties>.*)\}$")
SFS_LOG_NAME_RE = re.compile(r"^sfslog\.\d+\.gz$", re.IGNORECASE)


class SamsungSFSLogs(AndroidQFModule):
    """Parse USB and ADB events from Samsung system framework logs."""

    slug = "samsung_sfs_logs"

    @staticmethod
    def _parse_timestamp(value: str) -> Optional[str]:
        try:
            timestamp = datetime.datetime.strptime(
                value, "%y-%m-%d (GMT%z) %H:%M:%S.%f"
            )
        except ValueError:
            return None

        return convert_datetime_to_iso(timestamp)

    @staticmethod
    def _parse_adb_key(timestamp: str, message: str) -> Optional[dict]:
        match = ADB_KEY_RE.match(message)
        if not match:
            return None

        state = int(match["state"])
        key_info = DumpsysADBArtifact.calculate_key_info(
            match["key"].encode("utf-8")
        )
        return {
            "timestamp": timestamp,
            "event": "adb_connection",
            "key": key_info["key"].decode("utf-8", errors="replace"),
            "user": key_info["user"],
            "fingerprint": key_info["fingerprint"],
            "state": state,
            "state_name": ADB_STATES.get(state, "unknown"),
            "always_allow": match["always_allow"] == "true",
            "last_connection_time": int(match["last_connection_time"]),
            "auth_window": int(match["auth_window"]),
        }

    @staticmethod
    def _parse_usb_device(timestamp: str, message: str) -> Optional[dict]:
        match = USB_DEVICE_RE.match(message)
        if not match:
            return None

        return {
            "timestamp": timestamp,
            "event": "usb_device_attached",
            "vendor_id": match["vendor_id"],
            "product_id": match["product_id"],
            "manufacturer": match["manufacturer"],
            "product": match["product"],
            "version": match["version"],
            "serial": match["serial"],
            "has_audio": match["has_audio"] == "true",
            "has_hid": match["has_hid"] == "true",
            "has_storage": match["has_storage"] == "true",
        }

    @staticmethod
    def _parse_usb_uevent(timestamp: str, message: str) -> Optional[dict]:
        match = USB_UEVENT_RE.match(message)
        if not match:
            return None

        properties = {}
        for item in match["properties"].split(","):
            key, separator, value = item.strip().partition("=")
            if separator:
                properties[key] = value

        if "USB_STATE" not in properties:
            return None

        return {
            "timestamp": timestamp,
            "event": "usb_state",
            "usb_state": properties["USB_STATE"],
            "subsystem": properties.get("SUBSYSTEM"),
            "sequence_number": properties.get("SEQNUM"),
            "action": properties.get("ACTION"),
            "device_path": properties.get("DEVPATH"),
        }

    @classmethod
    def parse_line(cls, line: str) -> Optional[dict]:
        match = LOG_LINE_RE.match(line.rstrip())
        if not match:
            return None

        timestamp = cls._parse_timestamp(match["timestamp"])
        if not timestamp:
            return None

        if match["tag"] == "AdbDebuggingManager":
            return cls._parse_adb_key(timestamp, match["message"])
        if match["tag"] == "UsbHostManager":
            return cls._parse_usb_device(timestamp, match["message"])
        if match["tag"] == "UsbDeviceManager":
            return cls._parse_usb_uevent(timestamp, match["message"])

        return None

    def _get_sfs_logs(self) -> list[str]:
        return [
            file_path
            for file_path in self.files
            if SFS_LOG_NAME_RE.match(
                file_path.replace("\\", "/").rsplit("/", 1)[-1]
            )
        ]

    def _open_file(self, file_path: str) -> IO[bytes]:
        if self.archive:
            return self.archive.open(file_path)
        if not self.parent_path:
            raise ValueError("parent_path is not set")
        return open(os.path.join(self.parent_path, file_path), "rb")

    def run(self) -> None:
        sfs_logs = self._get_sfs_logs()
        if not sfs_logs:
            self.log.info("No Samsung sfslog files found")
            return

        for file_path in sfs_logs:
            try:
                with self._open_file(file_path) as compressed:
                    with gzip.GzipFile(fileobj=compressed) as gzip_file:
                        with io.TextIOWrapper(
                            gzip_file, encoding="utf-8", errors="replace"
                        ) as text_file:
                            for line in text_file:
                                result = self.parse_line(line)
                                if result:
                                    result["source_file"] = file_path.replace("\\", "/")
                                    self.results.append(result)
            except (EOFError, OSError) as exc:
                self.log.warning(
                    'Unable to read Samsung system framework log "%s": %s',
                    file_path,
                    exc,
                )

        self.log.info(
            "Extracted a total of %d Samsung USB and ADB events",
            len(self.results),
        )

    def check_indicators(self) -> None:
        return

    def serialize(
        self, record: ModuleAtomicResult
    ) -> ModuleSerializedResult:
        event = record["event"]
        if event == "adb_connection":
            data = (
                f"ADB key {record['fingerprint'] or '<unknown>'} "
                f"({record['user'] or 'unknown user'}): {record['state_name']}"
            )
        elif event == "usb_device_attached":
            data = (
                f"USB device {record['vendor_id']}:{record['product_id']} attached "
                f"({record['manufacturer']} {record['product']})"
            )
        else:
            data = f"USB state changed to {record['usb_state']}"
            if record.get("device_path"):
                data += f" at {record['device_path']}"

        return {
            "timestamp": record["timestamp"],
            "module": self.__class__.__name__,
            "event": event,
            "data": data,
        }
