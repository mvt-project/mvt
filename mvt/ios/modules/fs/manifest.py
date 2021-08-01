# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 MVT Project Developers.
# See the file 'LICENSE' for usage and copying permissions, or find a copy at
#   https://github.com/mvt-project/mvt/blob/main/LICENSE

import datetime
import io
import os
import sqlite3

import biplist

from mvt.common.utils import convert_timestamp_to_iso
from mvt.common.module import DatabaseNotFoundError

from .base import IOSExtraction


class Manifest(IOSExtraction):
    """This module extracts information from a backup Manifest.db file."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def _get_key(self, dictionary, key):
        """
        Unserialized plist objects can have keys which are str or byte types

        This is a helper to try fetch a key as both a byte or string type.
        """
        return dictionary.get(key.encode("utf-8"), None) or dictionary.get(key, None)

    def _convert_timestamp(self, timestamp_or_unix_time_int):
        """Older iOS versions stored the manifest times as unix timestamps."""
        if isinstance(timestamp_or_unix_time_int, datetime.datetime):
            return convert_timestamp_to_iso(timestamp_or_unix_time_int)
        else:
            timestamp = datetime.datetime.utcfromtimestamp(timestamp_or_unix_time_int)
            return convert_timestamp_to_iso(timestamp)

    def serialize(self, record):
        records = []
        if "modified" not in record or "statusChanged" not in record:
            return
        for ts in set([record["created"], record["modified"], record["statusChanged"]]):
            macb = ""
            macb += "M" if ts == record["modified"] else "-"
            macb += "-"
            macb += "C" if ts == record["statusChanged"] else "-"
            macb += "B" if ts == record["created"] else "-"

            records.append({
                "timestamp": ts,
                "module": self.__class__.__name__,
                "event": macb,
                "data": f"{record['relativePath']} - {record['domain']}"
            })

        return records

    def check_indicators(self):
        if not self.indicators:
            return

        for result in self.results:
            if not "relativePath" in result:
                continue
            if not result["relativePath"]:
                continue

            if result["domain"]:
                if os.path.basename(result["relativePath"]) == "com.apple.CrashReporter.plist" and result["domain"] == "RootDomain":
                    self.log.warning("Found a potentially suspicious \"com.apple.CrashReporter.plist\" file created in RootDomain")
                    self.detected.append(result)
                    continue

            if self.indicators.check_file(result["relativePath"]):
                self.log.warning("Found a known malicious file at path: %s", result["relativePath"])
                self.detected.append(result)
                continue

            relPath = result["relativePath"].lower()
            for ioc in self.indicators.ioc_domains:
                if ioc.lower() in relPath:
                    self.log.warning("Found mention of domain \"%s\" in a backup file with path: %s",
                                     ioc, relPath)
                    self.detected.append(result)

    def run(self):
        manifest_db_path = os.path.join(self.base_folder, "Manifest.db")
        if not os.path.isfile(manifest_db_path):
            raise DatabaseNotFoundError("Impossible to find the module's database file")

        self.log.info("Found Manifest.db database at path: %s", manifest_db_path)

        conn = sqlite3.connect(manifest_db_path)
        cur = conn.cursor()

        cur.execute("SELECT * FROM Files;")
        names = [description[0] for description in cur.description]

        for file_entry in cur:
            file_data = dict()
            for index, value in enumerate(file_entry):
                file_data[names[index]] = value

            cleaned_metadata = {
                "fileID": file_data["fileID"],
                "domain": file_data["domain"],
                "relativePath": file_data["relativePath"],
                "flags": file_data["flags"],
                "created": "",
            }

            if file_data["file"]:
                try:
                    file_plist = biplist.readPlist(io.BytesIO(file_data["file"]))
                    file_metadata = self._get_key(file_plist, "$objects")[1]
                    cleaned_metadata.update({
                        "created": self._convert_timestamp(self._get_key(file_metadata, "Birth")),
                        "modified": self._convert_timestamp(self._get_key(file_metadata, "LastModified")),
                        "statusChanged": self._convert_timestamp(self._get_key(file_metadata, "LastStatusChange")),
                        "mode": oct(self._get_key(file_metadata, "Mode")),
                        "owner": self._get_key(file_metadata, "UserID"),
                        "size": self._get_key(file_metadata, "Size"),
                    })
                except:
                    self.log.exception("Error reading manifest file metadata")
                    pass

            self.results.append(cleaned_metadata)

        cur.close()
        conn.close()

        self.log.info("Extracted a total of %d file metadata items", len(self.results))
