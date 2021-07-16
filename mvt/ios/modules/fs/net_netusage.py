# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 MVT Project Developers.
# See the file 'LICENSE' for usage and copying permissions, or find a copy at
#   https://github.com/mvt-project/mvt/blob/main/LICENSE

from .net_base import NetBase

NETUSAGE_ROOT_PATHS = [
    "private/var/networkd/netusage.sqlite",
    "private/var/networkd/db/netusage.sqlite"
]

class Netusage(NetBase):
    """This class extracts data from netusage.sqlite and attempts to identify
    any suspicious processes if running on a full filesystem dump."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def run(self):
        self._find_ios_database(root_paths=NETUSAGE_ROOT_PATHS)
        self.log.info("Found NetUsage database at path: %s", self.file_path)

        self._extract_net_data()
        self._find_suspicious_processes()
