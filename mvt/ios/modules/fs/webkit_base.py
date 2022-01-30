# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import datetime
import os

from mvt.common.utils import convert_timestamp_to_iso

from ..base import IOSExtraction


class WebkitBase(IOSExtraction):
    """This class is a base for other WebKit-related modules."""

    def check_indicators(self):
        if not self.indicators:
            return

        for result in self.results:
            ioc = self.indicators.check_domain(result["url"])
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)

    def _process_webkit_folder(self, root_paths):
        for found_path in self._get_fs_files_from_patterns(root_paths):
            key = os.path.relpath(found_path, self.base_folder)

            for name in os.listdir(found_path):
                if not name.startswith("http"):
                    continue

                name = name.replace("http_", "http://")
                name = name.replace("https_", "https://")
                url = name.split("_")[0]

                self.results.append({
                    "folder": key,
                    "url": url,
                    "isodate": convert_timestamp_to_iso(datetime.datetime.utcfromtimestamp(os.stat(found_path).st_mtime)),
                })
