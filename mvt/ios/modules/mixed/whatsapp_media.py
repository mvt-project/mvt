# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import io
import logging
import sqlite3
import plistlib

from mvt.common.utils import (convert_mactime_to_unix, convert_timestamp_to_iso)

from ..base import IOSExtraction

log = logging.getLogger(__name__)

WHATSAPP_BACKUP_IDS = [
    "7c7fba66680ef796b916b067077cc246adacf01d",
]
WHATSAPP_ROOT_PATHS = [
    "private/var/mobile/Containers/Shared/AppGroup/*/ChatStorage.sqlite",
]


class WhatsappMedia(IOSExtraction):
    """This module extracts all WhatsApp media containing links."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record):
        if "isodate" in record:
            if record["table"] == "ZWAMEDIAITEM":
                return {
                    "timestamp": record.get("isodate"),
                    "module": self.__class__.__name__,
                    "event": "MediaItem",
                    "data": record.get("ZMEDIAURL", "")
                }
            else:
                if record["ZCONTENT1"] == record["ZCONTENT2"]:
                    link = record["ZCONTENT1"]
                else:
                    link = "{} ({})".format(record["ZCONTENT1"], record["ZCONTENT2"])
                return {
                    "timestamp": record.get("isodate"),
                    "module": self.__class__.__name__,
                    "event": "MessageDataItem",
                    "data": link
                }

    def check_indicators(self):
        if not self.indicators:
            return

        for item in self.results:
            if item.get("ZMEDIAURL", None):
                # Filtering local images for performance
                if not item["ZMEDIAURL"].startswith("https://mmg-fna.whatsapp.net/"):
                    #print(item["ZMEDIAURL"])
                    if self.indicators.check_domain(item["ZMEDIAURL"]):
                        self.detected.append(item)
            if item.get("ZCONTENT1", None):
                if self.indicators.check_domain(item["ZCONTENT1"]):
                    self.detected.append(item)
                else:
                    if item["ZCONTENT2"] != item["ZCONTENT1"]:
                        if self.indicators.check_domain(item["ZCONTENT2"]):
                            self.detected.append(item)

    def run(self):
        self._find_ios_database(backup_ids=WHATSAPP_BACKUP_IDS,
                                root_paths=WHATSAPP_ROOT_PATHS)
        log.info("Found WhatsApp database at path: %s", self.file_path)

        conn = sqlite3.connect(self.file_path)
        cur = conn.cursor()

        # Start with ZWAMEDIAITEM
        cur.execute("SELECT * FROM ZWAMEDIAITEM;")
        names = [description[0] for description in cur.description]

        for item in cur:
            new_item = {}
            for index, value in enumerate(item):
                new_item[names[index]] = value
            # Removing mediakey that is not useful
            new_item.pop("ZMEDIAKEY")
            new_item["table"] = "ZWAMEDIAITEM"

            if not new_item.get("ZMEDIAURL", None):
                continue

            # We convert Mac's silly timestamp again.
            if new_item.get("ZMEDIAURLDATE", None):
                new_item["isodate"] = convert_timestamp_to_iso(
                    convert_mactime_to_unix(new_item.get("ZMEDIAURLDATE")))

            # Extracting metadata
            if new_item["ZMETADATA"]:
                if not new_item["ZMEDIAURL"].startswith("https://mmg-fna.whatsapp.net/"):
                    try:
                        metadata_plist = plistlib.load(io.BytesIO(new_item["ZMETADATA"]))
                        # Filtering on useful data
                        new_item["ZMETADATA"] = [entry
                                                 for entry in metadata_plist['$objects']
                                                 if isinstance(entry, str)
                                                ]
                    except Exception:
                        new_item.pop("ZMETADATA")
                else:
                    new_item.pop("ZMETADATA")
            self.results.append(new_item)

        # ZWAMESSAGEDATAITEM
        cur.execute("SELECT * FROM ZWAMESSAGEDATAITEM;")
        names = [description[0] for description in cur.description]
        for item in cur:
            new_item = {}
            for index, value in enumerate(item):
                new_item[names[index]] = value
            new_item["table"] = "ZWAMESSAGEDATAITEM"

            # We convert Mac's silly timestamp again.
            if new_item.get("ZDATE", None):
                new_item["isodate"] = convert_timestamp_to_iso(
                    convert_mactime_to_unix(new_item.get("ZDATE")))
            self.results.append(new_item)

        cur.close()
        conn.close()

        log.info("Extracted a total of %d WhatsApp media items", len(self.results))
