# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import os
import plistlib

from mvt.common.utils import convert_timestamp_to_iso

from ..base import IOSExtraction

WEBKIT_SESSION_RESOURCE_LOG_BACKUP_IDS = [
    "a500ee38053454a02e990957be8a251935e28d3f",
]
WEBKIT_SESSION_RESOURCE_LOG_BACKUP_RELPATH = "Library/WebKit/WebsiteData/ResourceLoadStatistics/full_browsing_session_resourceLog.plist"
WEBKIT_SESSION_RESOURCE_LOG_ROOT_PATHS = [
    "private/var/mobile/Containers/Data/Application/*/SystemData/com.apple.SafariViewService/Library/WebKit/WebsiteData/full_browsing_session_resourceLog.plist",
    "private/var/mobile/Containers/Data/Application/*/Library/WebKit/WebsiteData/ResourceLoadStatistics/full_browsing_session_resourceLog.plist",
    "private/var/mobile/Library/WebClips/*/Storage/full_browsing_session_resourceLog.plist",
]


class WebkitSessionResourceLog(IOSExtraction):
    """This module extracts records from WebKit browsing session
    resource logs, and checks them against any provided list of
    suspicious domains.


    """

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

        self.results = {} if not results else results

    @staticmethod
    def _extract_domains(entries):
        if not entries:
            return []

        domains = []
        for entry in entries:
            if "origin" in entry:
                domains.append(entry["origin"])
            if "domain" in entry:
                domains.append(entry["domain"])

        return domains

    def check_indicators(self):
        if not self.indicators:
            return

        for key, entries in self.results.items():
            for entry in entries:
                source_domains = self._extract_domains(entry["redirect_source"])
                destination_domains = self._extract_domains(entry["redirect_destination"])

                # TODO: Currently not used.
                # subframe_origins = self._extract_domains(entry["subframe_under_origin"])
                # subresource_domains = self._extract_domains(entry["subresource_under_origin"])

                all_origins = set([entry["origin"]] + source_domains + destination_domains)

                ioc = self.indicators.check_domains(all_origins)
                if ioc:
                    entry["matched_indicator"] = ioc
                    self.detected.append(entry)

                    redirect_path = ""
                    if len(source_domains) > 0:
                        redirect_path += "SOURCE: "
                        for idx, item in enumerate(source_domains):
                            source_domains[idx] = f"\"{item}\""

                        redirect_path += ", ".join(source_domains)
                        redirect_path += " -> "

                    redirect_path += f"ORIGIN: \"{entry['origin']}\""

                    if len(destination_domains) > 0:
                        redirect_path += " -> "
                        redirect_path += "DESTINATION: "
                        for idx, item in enumerate(destination_domains):
                            destination_domains[idx] = f"\"{item}\""

                        redirect_path += ", ".join(destination_domains)

                    self.log.warning("Found HTTP redirect between suspicious domains: %s", redirect_path)

    def _extract_browsing_stats(self, log_path):
        items = []

        with open(log_path, "rb") as handle:
            file_plist = plistlib.load(handle)

        if "browsingStatistics" not in file_plist:
            return items

        browsing_stats = file_plist["browsingStatistics"]

        for item in browsing_stats:
            items.append({
                "origin": item.get("PrevalentResourceOrigin", ""),
                "redirect_source": item.get("topFrameUniqueRedirectsFrom", ""),
                "redirect_destination": item.get("topFrameUniqueRedirectsTo", ""),
                "subframe_under_origin": item.get("subframeUnderTopFrameOrigins", ""),
                "subresource_under_origin": item.get("subresourceUnderTopFrameOrigins", ""),
                "user_interaction": item.get("hadUserInteraction"),
                "most_recent_interaction": convert_timestamp_to_iso(item["mostRecentUserInteraction"]),
                "last_seen": convert_timestamp_to_iso(item["lastSeen"]),
            })

        return items

    def run(self):
        if self.is_backup:
            for log_file in self._get_backup_files_from_manifest(relative_path=WEBKIT_SESSION_RESOURCE_LOG_BACKUP_RELPATH):
                log_path = self._get_backup_file_from_id(log_file["file_id"])
                if not log_path:
                    continue
                self.log.info("Found Safari browsing session resource log at path: %s", log_path)
                self.results[log_path] = self._extract_browsing_stats(log_path)
        elif self.is_fs_dump:
            for log_path in self._get_fs_files_from_patterns(WEBKIT_SESSION_RESOURCE_LOG_ROOT_PATHS):
                self.log.info("Found Safari browsing session resource log at path: %s", log_path)
                key = os.path.relpath(log_path, self.base_folder)
                self.results[key] = self._extract_browsing_stats(log_path)

        self.log.info("Extracted records from %d Safari browsing session resource logs",
                      len(self.results))
