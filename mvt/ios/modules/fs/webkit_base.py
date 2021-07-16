# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 MVT Project Developers.
# See the file 'LICENSE' for usage and copying permissions, or find a copy at
#   https://github.com/mvt-project/mvt/blob/main/LICENSE

import os
import datetime

from .base import IOSExtraction

from mvt.common.utils import convert_timestamp_to_iso

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
