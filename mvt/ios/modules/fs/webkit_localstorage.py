# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional, Union

from .webkit_base import WebkitBase

WEBKIT_LOCALSTORAGE_ROOT_PATHS = [
    "private/var/mobile/Containers/Data/Application/*/Library/WebKit/WebsiteData/LocalStorage/",
]


class WebkitLocalStorage(WebkitBase):
    """This module looks extracts records from WebKit LocalStorage folders,
    and checks them against any provided list of suspicious domains.


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
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": "webkit_local_storage",
            "data": f"WebKit Local Storage folder {record['folder']} "
            f"containing file for URL {record['url']}",
        }

    def run(self) -> None:
        self._process_webkit_folder(WEBKIT_LOCALSTORAGE_ROOT_PATHS)
        self.log.info(
            "Extracted a total of %d records from WebKit Local Storages",
            len(self.results),
        )
