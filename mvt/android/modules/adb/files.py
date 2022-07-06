# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import datetime
import logging
import os
import stat

from mvt.common.utils import convert_timestamp_to_iso

from .base import AndroidExtraction

log = logging.getLogger(__name__)

ANDROID_TMP_FOLDERS = [
    "/tmp/",
    "/data/local/tmp/",
]
ANDROID_MEDIA_FOLDERS = [
    "/data/media/0",
    "/sdcard/",
]


class Files(AndroidExtraction):
    """This module extracts the list of files on the device."""

    def __init__(self, file_path: str = None, target_path: str = None,
                 results_path: str = None, fast_mode: bool = False,
                 log: logging.Logger = None, results: list = []) -> None:
        super().__init__(file_path=file_path, target_path=target_path,
                         results_path=results_path, fast_mode=fast_mode,
                         log=log, results=results)
        self.full_find = False

    def serialize(self, record: dict) -> None:
        if "modified_time" in record:
            return {
                "timestamp": record["modified_time"],
                "module": self.__class__.__name__,
                "event": "file_modified",
                "data": record["path"],
            }

    def check_indicators(self) -> None:
        for result in self.results:
            if result.get("is_suid"):
                self.log.warning("Found an SUID file in a non-standard directory \"%s\".",
                                 result["path"])

            if self.indicators and self.indicators.check_file_path(result["path"]):
                self.log.warning("Found a known suspicous file at path: \"%s\"", result["path"])
                self.detected.append(result)

    def backup_file(self, file_path: str) -> None:
        local_file_name = file_path.replace("/", "_").replace(" ", "-")
        local_files_folder = os.path.join(self.results_path, "files")
        if not os.path.exists(local_files_folder):
            os.mkdir(local_files_folder)

        local_file_path = os.path.join(local_files_folder, local_file_name)

        try:
            self._adb_download(remote_path=file_path,
                               local_path=local_file_path)
        except Exception:
            pass
        else:
            self.log.info("Downloaded file %s to local copy at %s",
                          file_path, local_file_path)

    def find_files(self, folder: str) -> None:
        if self.full_find:
            output = self._adb_command(f"find '{folder}' -type f -printf '%T@ %m %s %u %g %p\n' 2> /dev/null")

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
            output = self._adb_command(f"find '{folder}' -type f 2> /dev/null")
            for file_line in output.splitlines():
                self.results.append({"path": file_line.rstrip()})

    def run(self) -> None:
        self._adb_connect()

        output = self._adb_command("find '/' -maxdepth 1 -printf '%T@ %m %s %u %g %p\n' 2> /dev/null")
        if output or output.strip().splitlines():
            self.full_find = True

        for tmp_folder in ANDROID_TMP_FOLDERS:
            self.find_files(tmp_folder)

        for entry in self.results:
            self.log.info("Found file in tmp folder at path %s",
                          entry.get("path"))
            if self.results_path:
                self.backup_file(entry.get("path"))

        for media_folder in ANDROID_MEDIA_FOLDERS:
            self.find_files(media_folder)

        self.log.info("Found %s files in primary Android tmp and media folders",
                      len(self.results))

        if self.fast_mode:
            self.log.info("Flag --fast was enabled: skipping full file listing")
        else:
            self.log.info("Processing full file listing. This may take a while...")
            self.find_files("/")

            self.log.info("Found %s total files", len(self.results))

        self._adb_disconnect()
