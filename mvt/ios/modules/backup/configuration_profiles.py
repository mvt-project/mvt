# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import plistlib
from base64 import b64encode

from ..base import IOSExtraction

CONF_PROFILES_DOMAIN = "SysSharedContainerDomain-systemgroup.com.apple.configurationprofiles"

class ConfigurationProfiles(IOSExtraction):
    """This module extracts the full plist data from configuration profiles."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def run(self):
        for conf_file in self._get_backup_files_from_manifest(domain=CONF_PROFILES_DOMAIN):
            conf_file_path = self._get_backup_file_from_id(conf_file["file_id"])
            if not conf_file_path:
                continue

            with open(conf_file_path, "rb") as handle:
                conf_plist = plistlib.load(handle)

            if "SignerCerts" in conf_plist:
                conf_plist["SignerCerts"] = [b64encode(x) for x in conf_plist["SignerCerts"]]

            self.results.append({
                "file_id": conf_file["file_id"],
                "relative_path": conf_file["relative_path"],
                "domain": conf_file["domain"],
                "plist": conf_plist,
            })

        self.log.info("Extracted details about %d configuration profiles", len(self.results))
