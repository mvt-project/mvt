# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from .webkit_base import WebkitBase

WEBKIT_LOCALSTORAGE_ROOT_PATHS = [
    "private/var/mobile/Containers/Data/Application/*/Library/WebKit/WebsiteData/LocalStorage/",
]


class WebkitLocalStorage(WebkitBase):
    """This module looks extracts records from WebKit LocalStorage folders,
    and checks them against any provided list of suspicious domains.


    """

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record):
        return {
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": "webkit_local_storage",
            "data": f"WebKit Local Storage folder {record['folder']} containing file for URL {record['url']}",
        }

    def run(self):
        self._process_webkit_folder(WEBKIT_LOCALSTORAGE_ROOT_PATHS)
        self.log.info("Extracted a total of %d records from WebKit Local Storages",
                      len(self.results))
