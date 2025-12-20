# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import hashlib
import logging
import os
import plistlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from mvt.common.module import DatabaseNotFoundError
from mvt.common.module_types import (
    ModuleAtomicResult,
    ModuleResults,
    ModuleSerializedResult,
)
from mvt.common.utils import convert_datetime_to_iso

from ..base import IOSExtraction

APPLICATIONS_DB_PATH = [
    "private/var/containers/Bundle/Application/*/iTunesMetadata.plist"
]
KNOWN_APP_INSTALLERS = [
    "com.apple.AppStore",
    "com.apple.AppStore.ProductPageExtension",
    "com.apple.dmd",
    "dmd",
]


class Applications(IOSExtraction):
    """Extract information from accounts installed on the phone."""

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        module_options: Optional[dict] = None,
        log: logging.Logger = logging.getLogger(__name__),
        results: ModuleResults = [],
    ) -> None:
        super().__init__(
            file_path=file_path,
            target_path=target_path,
            results_path=results_path,
            module_options=module_options,
            log=log,
            results=results,
        )

    def serialize(self, record: ModuleAtomicResult) -> ModuleSerializedResult:
        if "isodate" in record:
            return {
                "timestamp": record["isodate"],
                "module": self.__class__.__name__,
                "event": "app_installed",
                "data": f"App {record.get('name', '')} version {record.get('bundleShortVersionString', '')} from {record.get('artistName', '')} installed from {record.get('sourceApp', '')}",
            }
        return []

    def check_indicators(self) -> None:
        for result in self.results:
            if self.indicators:
                if "softwareVersionBundleId" not in result:
                    self.alertstore.high(
                        "Suspicious application identified without softwareVersionBundleId",
                        "",
                        result,
                    )
                    continue

                ioc_match = self.indicators.check_process(
                    result["softwareVersionBundleId"]
                )
                if ioc_match:
                    result["matched_indicator"] = ioc_match.ioc
                    self.alertstore.critical(
                        f"Malicious application {result['softwareVersionBundleId']} identified",
                        "",
                        result,
                        matched_indicator=ioc_match.ioc,
                    )
                    continue

                ioc_match = self.indicators.check_app_id(
                    result["softwareVersionBundleId"]
                )
                if ioc_match:
                    result["matched_indicator"] = ioc_match.ioc
                    self.alertstore.critical(
                        f"Malicious application {result['softwareVersionBundleId']} identified",
                        "",
                        result,
                        matched_indicator=ioc_match.ioc,
                    )
                    continue

            # Some apps installed from apple store with sourceApp "com.apple.AppStore.ProductPageExtension"
            if (
                result.get("sourceApp", "com.apple.AppStore")
                not in KNOWN_APP_INSTALLERS
            ):
                self.alertstore.medium(
                    f"Suspicious app not installed from the App Store or MDM: {result['softwareVersionBundleId']}",
                    "",
                    result,
                )

    def _parse_itunes_timestamp(self, entry: Dict[str, Any]) -> None:
        """
        Parse the iTunes metadata info
        """
        if entry.get("com.apple.iTunesStore.downloadInfo", {}).get(
            "purchaseDate", None
        ):
            timestamp = datetime.strptime(
                entry["com.apple.iTunesStore.downloadInfo"]["purchaseDate"],
                "%Y-%m-%dT%H:%M:%SZ",
            )
            timestamp_utc = timestamp.astimezone(timezone.utc)
            entry["isodate"] = convert_datetime_to_iso(timestamp_utc)

    def _parse_itunes_metadata(self, plist_path: str) -> None:
        """
        Parse iTunesMetadata.plist file from an application in fs dump
        """
        with open(plist_path, "rb") as f:
            entry = plistlib.load(f)

        entry["file_path"] = plist_path
        self._parse_itunes_timestamp(entry)
        self.results.append(entry)

    def _parse_info_plist(self, plist_path: str) -> None:
        """
        Parse Info.plist file from backup
        """
        with open(plist_path, "rb") as f:
            data = plistlib.load(f)

        for app in data.get("Applications", {}):
            app_data = data["Applications"][app]
            entry = {"name": app}
            metadata = plistlib.loads(app_data["iTunesMetadata"])
            entry.update(metadata)

            self._parse_itunes_timestamp(entry)

            if "PlaceholderIcon" in app_data:
                sha256_hash = hashlib.sha256()
                sha256_hash.update(app_data["PlaceholderIcon"])
                entry["icon_sha256"] = sha256_hash.hexdigest()

            self.results.append(entry)

    def run(self) -> None:
        if self.is_backup:
            if not self.target_path:
                return
            plist_path = os.path.join(self.target_path, "Info.plist")
            if not os.path.isfile(plist_path):
                raise DatabaseNotFoundError("Impossible to find Info.plist file")
            self._parse_info_plist(plist_path)
        elif self.is_fs_dump:
            for file_path in self._get_fs_files_from_patterns(APPLICATIONS_DB_PATH):
                self._parse_itunes_metadata(file_path)

        self.log.info("Extracted a total of %d applications", len(self.results))
