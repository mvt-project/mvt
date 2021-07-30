# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 MVT Project Developers.
# See the file 'LICENSE' for usage and copying permissions, or find a copy at
#   https://github.com/mvt-project/mvt/blob/main/LICENSE

import datetime
import os

from mvt.common.utils import convert_timestamp_to_iso

from .base import IOSExtraction


class Filesystem(IOSExtraction):
    """This module extracts creation and modification date of files from a
    full file-system dump."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record):
        return {
            "timestamp": record["modified"],
            "module": self.__class__.__name__,
            "event": f"file_modified",
            "data": record["file_path"],
        }

    def check_indicators(self):
        if not self.indicators:
            return

        for result in self.results:
            if self.indicators.check_file(result["file_path"]):
                self.detected.append(result)

    def run(self):
        for root, dirs, files in os.walk(self.base_folder):
            for file_name in files:
                try:
                    file_path = os.path.join(root, file_name)
                    result = {
                        "file_path": os.path.relpath(file_path, self.base_folder),
                        "modified": convert_timestamp_to_iso(datetime.datetime.utcfromtimestamp(os.stat(file_path).st_mtime)),
                    }
                except:
                    continue
                else:
                    self.results.append(result)
