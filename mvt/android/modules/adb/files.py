# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import datetime
import logging
import stat

from mvt.common.utils import convert_timestamp_to_iso

from .base import AndroidExtraction

log = logging.getLogger(__name__)


class Files(AndroidExtraction):
    """This module extracts the list of files on the device."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 serial=None, fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)
        self.full_find = False

    def find_files(self, folder):
        if self.full_find:
            output = self._adb_command(f"find '{folder}' -printf '%T@ %m %s %u %g %p\n' 2> /dev/null")

            for file_line in output.splitlines():
                [unix_timestamp, mode, size, owner, group, full_path] = file_line.rstrip().split(" ", 5)
                mod_time = convert_timestamp_to_iso(datetime.datetime.utcfromtimestamp(int(float(unix_timestamp))))
                self.results.append({
                    "path": full_path,
                    "modified_time": mod_time,
                    "mode": mode,
                    "is_suid": (int(mode, 8) & stat.S_ISUID) == 2048,
                    "is_sgid": (int(mode, 8) & stat.S_ISGID) == 1024,
                    "size": size,
                    "owner": owner,
                    "group": group,
                })
        else:
            output = self._adb_command(f"find '{folder}' 2> /dev/null")
            for file_line in output.splitlines():
                self.results.append({"path": file_line.rstrip()})

    def serialize(self, record):
        if "modified_time" in record:
            return {
                "timestamp": record["modified_time"],
                "module": self.__class__.__name__,
                "event": "file_modified",
                "data": record["path"],
            }

    def check_suspicious(self):
        """Check for files with suspicious permissions"""
        for result in sorted(self.results, key=lambda item: item["path"]):
            if result.get("is_suid"):
                self.log.warning("Found an SUID file in a non-standard directory \"%s\".",
                                 result["path"])
                self.detected.append(result)

    def check_indicators(self):
        """Check file list for known suspicious files or suspicious properties"""
        self.check_suspicious()

        if not self.indicators:
            return

        for result in self.results:
            if self.indicators.check_file_path(result["path"]):
                self.log.warning("Found a known suspicous file at path: \"%s\"", result["path"])
                self.detected.append(result)

    def run(self):
        self._adb_connect()

        output = self._adb_command("find '/' -maxdepth 1 -printf '%T@ %m %s %u %g %p\n' 2> /dev/null")
        if output or output.strip().splitlines():
            self.full_find = True

        for data_path in ["/data/local/tmp/", "/sdcard/", "/tmp/"]:
            self.find_files(data_path)

        self.log.info("Found %s files in primary Android data directories", len(self.results))

        if self.fast_mode:
            self.log.info("Flag --fast was enabled: skipping full file listing")
        else:
            self.log.info("Processing full file listing. This may take a while...")
            self.find_files("/")
            self.log.info("Found %s total files", len(self.results))

        self._adb_disconnect()
