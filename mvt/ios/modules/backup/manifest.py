# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import datetime
import io
import logging
import os
import plistlib
from typing import Optional

from mvt.common.module import DatabaseNotFoundError
from mvt.common.url import URL
from mvt.common.utils import convert_datetime_to_iso, convert_unix_to_iso

from ..base import IOSExtraction


class Manifest(IOSExtraction):
    """This module extracts information from a backup Manifest.db file."""

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

    def _get_key(self, dictionary, key):
        """Unserialized plist objects can have keys which are str or byte types
        This is a helper to try fetch a key as both a byte or string type.

        :param dictionary:
        :param key:

        """
        return dictionary.get(key.encode("utf-8"), None) or dictionary.get(key, None)

    @staticmethod
    def _convert_timestamp(timestamp_or_unix_time_int):
        """Older iOS versions stored the manifest times as unix timestamps.

        :param timestamp_or_unix_time_int:

        """
        if isinstance(timestamp_or_unix_time_int, datetime.datetime):
            return convert_datetime_to_iso(timestamp_or_unix_time_int)

        return convert_unix_to_iso(timestamp_or_unix_time_int)

    def serialize(self, record: dict) -> []:
        records = []
        if "modified" not in record or "status_changed" not in record:
            return records

        for timestamp in set(
            [record["created"], record["modified"], record["status_changed"]]
        ):
            macb = ""
            macb += "M" if timestamp == record["modified"] else "-"
            macb += "-"
            macb += "C" if timestamp == record["status_changed"] else "-"
            macb += "B" if timestamp == record["created"] else "-"

            records.append(
                {
                    "timestamp": timestamp,
                    "module": self.__class__.__name__,
                    "event": macb,
                    "data": f"{record['relative_path']} - {record['domain']}",
                }
            )

        return records

    def check_indicators(self) -> None:
        for result in self.results:
            if not result.get("relative_path"):
                continue

            if not self.indicators:
                continue

            if self.indicators.check_file_path("/" + result["relative_path"]):
                self.detected.append(result)
                continue

            rel_path = result["relative_path"].lower()
            parts = rel_path.split("_")
            for part in parts:
                try:
                    URL(part)
                except Exception:
                    continue

                ioc = self.indicators.check_domain(part)
                if ioc:
                    self.log.warning(
                        'Found mention of domain "%s" in a backup file with '
                        "path: %s",
                        ioc["value"],
                        rel_path,
                    )
                    result["matched_indicator"] = ioc
                    self.detected.append(result)

    def run(self) -> None:
        manifest_db_path = os.path.join(self.target_path, "Manifest.db")
        if not os.path.isfile(manifest_db_path):
            raise DatabaseNotFoundError("unable to find backup's Manifest.db")

        self.log.info("Found Manifest.db database at path: %s", manifest_db_path)

        conn = self._open_sqlite_db(manifest_db_path)
        cur = conn.cursor()

        cur.execute("SELECT * FROM Files;")
        names = [description[0] for description in cur.description]

        for file_entry in cur:
            file_data = {}
            for index, value in enumerate(file_entry):
                file_data[names[index]] = value

            cleaned_metadata = {
                "file_id": file_data["fileID"],
                "domain": file_data["domain"],
                "relative_path": file_data["relativePath"],
                "flags": file_data["flags"],
                "created": "",
            }

            if file_data["file"]:
                try:
                    file_plist = plistlib.load(io.BytesIO(file_data["file"]))
                    file_metadata = self._get_key(file_plist, "$objects")[1]

                    birth = self._get_key(file_metadata, "Birth")
                    last_modified = self._get_key(file_metadata, "LastModified")
                    last_status_change = self._get_key(
                        file_metadata, "LastStatusChange"
                    )

                    cleaned_metadata.update(
                        {
                            "created": self._convert_timestamp(birth),
                            "modified": self._convert_timestamp(last_modified),
                            "status_changed": self._convert_timestamp(
                                last_status_change
                            ),
                            "mode": oct(self._get_key(file_metadata, "Mode")),
                            "owner": self._get_key(file_metadata, "UserID"),
                            "size": self._get_key(file_metadata, "Size"),
                        }
                    )
                except Exception:
                    self.log.exception(
                        "Error reading manifest file metadata for file with ID %s "
                        "and relative path %s",
                        file_data["fileID"],
                        file_data["relativePath"],
                    )

            self.results.append(cleaned_metadata)

        cur.close()
        conn.close()

        self.log.info("Extracted a total of %d file metadata items", len(self.results))
