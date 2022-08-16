# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional

from .webkit_base import WebkitBase

WEBKIT_SAFARIVIEWSERVICE_ROOT_PATHS = [
    "private/var/mobile/Containers/Data/Application/*/SystemData/com.apple.SafariViewService/Library/WebKit/WebsiteData/", # pylint: disable=line-too-long
]


class WebkitSafariViewService(WebkitBase):
    """This module looks extracts records from WebKit LocalStorage folders,
    and checks them against any provided list of suspicious domains.


    """

    def __init__(
        self,
        file_path: Optional[str] = "",
        target_path: Optional[str] = "",
        results_path: Optional[str] = "",
        fast_mode: Optional[bool] = False,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[list] = []
    ) -> None:
        super().__init__(file_path=file_path, target_path=target_path,
                         results_path=results_path, fast_mode=fast_mode,
                         log=log, results=results)

    def run(self) -> None:
        self._process_webkit_folder(WEBKIT_SAFARIVIEWSERVICE_ROOT_PATHS)
        self.log.info("Extracted a total of %d records from WebKit SafariViewService WebsiteData",
                      len(self.results))
