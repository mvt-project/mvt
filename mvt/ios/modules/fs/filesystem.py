# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
import os
from typing import Optional, Union

from mvt.common.utils import convert_unix_to_iso

from ..base import IOSExtraction


class Filesystem(IOSExtraction):
    """This module extracts creation and modification date of files from a
    full file-system dump.
    """

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

    def serialize(self, record: dict) -> Union[dict, list]:
        return {
            "timestamp": record["modified"],
            "module": self.__class__.__name__,
            "event": "entry_modified",
            "data": record["path"],
        }

    def check_indicators(self) -> None:
        if not self.indicators:
            return

        for result in self.results:
            if "path" not in result:
                continue

            ioc = self.indicators.check_file_path(result["path"])
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)

            # If we are instructed to run fast, we skip the rest.
            if self.module_options.get("fast_mode", None):
                continue

            ioc = self.indicators.check_file_path_process(result["path"])
            if ioc:
                result["matched_indicator"] = ioc
                self.detected.append(result)

    def run(self) -> None:
        for root, dirs, files in os.walk(self.target_path):
            for dir_name in dirs:
                try:
                    dir_path = os.path.join(root, dir_name)
                    result = {
                        "path": os.path.relpath(dir_path, self.target_path),
                        "modified": convert_unix_to_iso(os.stat(dir_path).st_mtime),
                    }
                except Exception:
                    continue
                else:
                    self.results.append(result)

            for file_name in files:
                try:
                    file_path = os.path.join(root, file_name)
                    result = {
                        "path": os.path.relpath(file_path, self.target_path),
                        "modified": convert_unix_to_iso(os.stat(file_path).st_mtime),
                    }
                except Exception:
                    continue
                else:
                    self.results.append(result)
