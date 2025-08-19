# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import datetime
import json
import logging

try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo
from typing import Optional, Union

from mvt.android.modules.androidqf.base import AndroidQFModule
from mvt.common.utils import convert_datetime_to_iso

SUSPICIOUS_PATHS = [
    "/data/local/tmp/",
]


class Files(AndroidQFModule):
    """This module analyse list of files"""

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

    def serialize(self, record: dict) -> Union[dict, list]:
        records = []

        for ts in set(
            [record["access_time"], record["changed_time"], record["modified_time"]]
        ):
            macb = ""
            macb += "M" if ts == record["modified_time"] else "-"
            macb += "A" if ts == record["access_time"] else "-"
            macb += "C" if ts == record["changed_time"] else "-"
            macb += "-"

            msg = record["path"]
            if record["context"]:
                msg += f" ({record['context']})"

            records.append(
                {
                    "timestamp": ts,
                    "module": self.__class__.__name__,
                    "event": macb,
                    "data": msg,
                }
            )

        return records

    def file_is_executable(self, mode_string):
        return "x" in mode_string

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_file_path(result["path"])
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)
                continue

            # NOTE: Update with final path used for Android collector.
            if result["path"] == "/data/local/tmp/collector":
                continue

            for suspicious_path in SUSPICIOUS_PATHS:
                if result["path"].startswith(suspicious_path):
                    file_type = ""
                    if self.file_is_executable(result["mode"]):
                        file_type = "executable "

                    self.log.warning(
                        'Found %sfile at suspicious path "%s".',
                        file_type,
                        result["path"],
                    )
                    self.detected.append(result)

            if result.get("sha256", "") == "":
                continue

            ioc = self.indicators.check_file_hash(result["sha256"])
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)

            # TODO: adds SHA1 and MD5 when available in MVT

    def run(self) -> None:
        if timezone := self._get_device_timezone():
            try:
                device_timezone = zoneinfo.ZoneInfo(timezone)
            except zoneinfo.ZoneInfoNotFoundError:
                self.log.warning("Device timezone '%s' not found, using UTC", timezone)
                device_timezone = datetime.timezone.utc
        else:
            self.log.warning("Unable to determine device timezone, using UTC")
            try:
                device_timezone = zoneinfo.ZoneInfo("UTC")
            except zoneinfo.ZoneInfoNotFoundError:
                # Fallback for Windows systems where zoneinfo might not have UTC
                device_timezone = datetime.timezone.utc

        for file in self._get_files_by_pattern("*/files.json"):
            rawdata = self._get_file_content(file).decode("utf-8", errors="ignore")
            try:
                data = json.loads(rawdata)
            except json.decoder.JSONDecodeError:
                data = []
                for line in rawdata.split("\n"):
                    if line.strip() == "":
                        continue
                    data.append(json.loads(line))

            for file_data in data:
                for ts in ["access_time", "changed_time", "modified_time"]:
                    if ts in file_data:
                        utc_timestamp = datetime.datetime.fromtimestamp(
                            file_data[ts], tz=datetime.timezone.utc
                        )
                        # Convert the UTC timestamp to local tiem on Android device's local timezone
                        local_timestamp = utc_timestamp.astimezone(device_timezone)

                        # HACK: We only output the UTC timestamp in convert_datetime_to_iso, we
                        # set the timestamp timezone to UTC, to avoid the timezone conversion again.
                        local_timestamp = local_timestamp.replace(
                            tzinfo=datetime.timezone.utc
                        )
                        file_data[ts] = convert_datetime_to_iso(local_timestamp)

                self.results.append(file_data)

            break  # Only process the first matching file

        self.log.info("Found a total of %d files", len(self.results))
