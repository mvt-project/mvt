# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import datetime
import os

from mvt.common.utils import convert_timestamp_to_iso

from .base import IOSExtraction


class WebkitBase(IOSExtraction):
    """This class is a base for other WebKit-related modules."""

    def check_indicators(self):
        if not self.indicators:
            return

        for item in self.results:
            if self.indicators.check_domain(item["url"]):
                self.detected.append(item)

    def _database_from_path(self, root_paths):
        for found_path in self._find_paths(root_paths):
            key = os.path.relpath(found_path, self.base_folder)

            for name in os.listdir(found_path):
                if not name.startswith("http"):
                    continue

                name = name.replace("http_", "http://")
                name = name.replace("https_", "https://")
                url = name.split("_")[0]

                self.results.append(dict(
                    folder=key,
                    url=url,
                    isodate=convert_timestamp_to_iso(datetime.datetime.utcfromtimestamp(os.stat(found_path).st_mtime)),
                ))
