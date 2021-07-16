# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 MVT Project Developers.
# See the file 'LICENSE' for usage and copying permissions, or find a copy at
#   https://github.com/mvt-project/mvt/blob/main/LICENSE

from .webkit_base import WebkitBase

WEBKIT_SAFARIVIEWSERVICE_ROOT_PATHS = [
    "private/var/mobile/Containers/Data/Application/*/SystemData/com.apple.SafariViewService/Library/WebKit/WebsiteData/",
]

class WebkitSafariViewService(WebkitBase):
    """This module looks extracts records from WebKit LocalStorage folders,
    and checks them against any provided list of suspicious domains."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def run(self):
        self._database_from_path(WEBKIT_SAFARIVIEWSERVICE_ROOT_PATHS)
