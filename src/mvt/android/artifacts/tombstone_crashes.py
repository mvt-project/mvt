# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import datetime
from typing import List, Optional, Union

import pydantic
import betterproto
from dateutil import parser

from mvt.common.utils import convert_datetime_to_iso
from mvt.android.parsers.proto.tombstone import Tombstone
from .artifact import AndroidArtifact


TOMBSTONE_DELIMITER = "*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***"

# Map the legacy crash file keys to the new format.
TOMBSTONE_TEXT_KEY_MAPPINGS = {
    "Build fingerprint": "build_fingerprint",
    "Revision": "revision",
    "ABI": "arch",
    "Timestamp": "timestamp",
    "Process uptime": "process_uptime",
    "Cmdline": "command_line",
    "pid": "pid",
    "tid": "tid",
    "name": "process_name",
    "binary_path": "binary_path",
    "uid": "uid",
    "signal": "signal_info",
    "code": "code",
    "Cause": "cause",
}


class SignalInfo(pydantic.BaseModel):
    code: int
    code_name: str
    name: str
    number: Optional[int] = None


class TombstoneCrashResult(pydantic.BaseModel):
    """
    MVT Result model for a tombstone crash result.

    Needed for validation and serialization, and consistency between text and protobuf tombstones.
    """

    file_name: str
    file_timestamp: str  # We store the timestamp as a string to avoid timezone issues
    build_fingerprint: str
    revision: str
    arch: Optional[str] = None
    timestamp: str  # We store the timestamp as a string to avoid timezone issues
    process_uptime: Optional[int] = None
    command_line: Optional[List[str]] = None
    pid: int
    tid: int
    process_name: Optional[str] = None
    binary_path: Optional[str] = None
    selinux_label: Optional[str] = None
    uid: int
    signal_info: SignalInfo
    cause: Optional[str] = None
    extra: Optional[str] = None


class TombstoneCrashArtifact(AndroidArtifact):
    """ "
    Parser for Android tombstone crash files.

    This parser can parse both text and protobuf tombstone crash files.
    """

    def serialize(self, record: dict) -> Union[dict, list]:
        return {
            "timestamp": record["timestamp"],
            "module": self.__class__.__name__,
            "event": "Tombstone",
            "data": (
                f"Crash in '{record['process_name']}' process running as UID '{record['uid']}' in file '{record['file_name']}' "
                f"Crash type '{record['signal_info']['name']}' with code '{record['signal_info']['code_name']}'"
            ),
        }

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_process(result["process_name"])
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)
                continue

            if result.get("command_line", []):
                command_name = result.get("command_line")[0].split("/")[-1]
                ioc = self.indicators.check_process(command_name)
                if ioc:
                    result["matched_indicator"] = ioc
                    self.detected.append(result)
                    continue

            SUSPICIOUS_UIDS = [
                0,  # root
                1000,  # system
                2000,  # shell
            ]
            if result["uid"] in SUSPICIOUS_UIDS:
                self.log.warning(
                    f"Potentially suspicious crash in process '{result['process_name']}' "
                    f"running as UID '{result['uid']}' in tombstone '{result['file_name']}' at {result['timestamp']}"
                )
                self.detected.append(result)

    def parse_protobuf(
        self, file_name: str, file_timestamp: datetime.datetime, data: bytes
    ) -> None:
        """
        Parse Android tombstone crash files from a protobuf object.
        """
        tombstone_pb = Tombstone().parse(data)
        tombstone_dict = tombstone_pb.to_dict(
            betterproto.Casing.SNAKE, include_default_values=True
        )

        # Add some extra metadata
        tombstone_dict["timestamp"] = self._parse_timestamp_string(
            tombstone_pb.timestamp
        )
        tombstone_dict["file_name"] = file_name
        tombstone_dict["file_timestamp"] = convert_datetime_to_iso(file_timestamp)
        tombstone_dict["process_name"] = self._proccess_name_from_thread(tombstone_dict)

        # Confirm the tombstone is valid, and matches the output model
        tombstone = TombstoneCrashResult.model_validate(tombstone_dict)
        self.results.append(tombstone.model_dump())

    def parse(
        self, file_name: str, file_timestamp: datetime.datetime, content: bytes
    ) -> None:
        """
        Parse text Android tombstone crash files.
        """

        # Split the tombstone file into a dictonary
        tombstone_dict = {
            "file_name": file_name,
            "file_timestamp": convert_datetime_to_iso(file_timestamp),
        }
        lines = content.decode("utf-8").splitlines()
        for line in lines:
            if not line.strip() or TOMBSTONE_DELIMITER in line:
                continue
            for key, destination_key in TOMBSTONE_TEXT_KEY_MAPPINGS.items():
                self._parse_tombstone_line(line, key, destination_key, tombstone_dict)

        # Validate the tombstone and add it to the results
        tombstone = TombstoneCrashResult.model_validate(tombstone_dict)
        self.results.append(tombstone.model_dump())

    def _parse_tombstone_line(
        self, line: str, key: str, destination_key: str, tombstone: dict
    ) -> bool:
        if not line.startswith(f"{key}"):
            return None

        if key == "pid":
            return self._load_pid_line(line, tombstone)
        elif key == "signal":
            return self._load_signal_line(line, tombstone)
        elif key == "Timestamp":
            return self._load_timestamp_line(line, tombstone)
        else:
            return self._load_key_value_line(line, key, destination_key, tombstone)

    def _load_key_value_line(
        self, line: str, key: str, destination_key: str, tombstone: dict
    ) -> bool:
        line_key, value = line.split(":", 1)
        if line_key != key:
            raise ValueError(f"Expected key {key}, got {line_key}")

        value_clean = value.strip().strip("'")
        if destination_key == "uid":
            tombstone[destination_key] = int(value_clean)
        elif destination_key == "process_uptime":
            # eg. "Process uptime: 40s"
            tombstone[destination_key] = int(value_clean.rstrip("s"))
        elif destination_key == "command_line":
            # XXX: Check if command line should be a single string in a list, or a list of strings.
            tombstone[destination_key] = [value_clean]
        else:
            tombstone[destination_key] = value_clean
        return True

    def _load_pid_line(self, line: str, tombstone: dict) -> bool:
        pid_part, tid_part, name_part = [part.strip() for part in line.split(",")]

        pid_key, pid_value = pid_part.split(":", 1)
        if pid_key != "pid":
            raise ValueError(f"Expected key pid, got {pid_key}")
        pid_value = int(pid_value.strip())

        tid_key, tid_value = tid_part.split(":", 1)
        if tid_key != "tid":
            raise ValueError(f"Expected key tid, got {tid_key}")
        tid_value = int(tid_value.strip())

        name_key, name_value = name_part.split(":", 1)
        if name_key != "name":
            raise ValueError(f"Expected key name, got {name_key}")
        name_value = name_value.strip()
        process_name, binary_path = self._parse_process_name(name_value, tombstone)

        tombstone["pid"] = pid_value
        tombstone["tid"] = tid_value
        tombstone["process_name"] = process_name
        tombstone["binary_path"] = binary_path
        return True

    def _parse_process_name(self, process_name_part, tombstone: dict) -> bool:
        process_name, process_path = process_name_part.split(">>>")
        process_name = process_name.strip()
        binary_path = process_path.strip().split(" ")[0]
        return process_name, binary_path

    def _load_signal_line(self, line: str, tombstone: dict) -> bool:
        signal, code, _ = [part.strip() for part in line.split(",", 2)]
        signal = signal.split("signal ")[1]
        signal_code, signal_name = signal.split(" ")
        signal_name = signal_name.strip("()")

        code_part = code.split("code ")[1]
        code_number, code_name = code_part.split(" ")
        code_name = code_name.strip("()")

        tombstone["signal_info"] = {
            "code": int(code_number),
            "code_name": code_name,
            "name": signal_name,
            "number": int(signal_code),
        }
        return True

    def _load_timestamp_line(self, line: str, tombstone: dict) -> bool:
        timestamp = line.split(":", 1)[1].strip()
        tombstone["timestamp"] = self._parse_timestamp_string(timestamp)
        return True

    @staticmethod
    def _parse_timestamp_string(timestamp: str) -> str:
        timestamp_parsed = parser.parse(timestamp)

        # HACK: Swap the local timestamp to UTC, so keep the original time and avoid timezone conversion.
        local_timestamp = timestamp_parsed.replace(tzinfo=datetime.timezone.utc)
        return convert_datetime_to_iso(local_timestamp)

    @staticmethod
    def _proccess_name_from_thread(tombstone_dict: dict) -> str:
        if tombstone_dict.get("threads"):
            for thread in tombstone_dict["threads"].values():
                if thread.get("id") == tombstone_dict["tid"] and thread.get("name"):
                    return thread["name"]
        return "Unknown"
