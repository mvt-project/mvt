# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional

from mvt.android.modules.adb.settings import ANDROID_DANGEROUS_SETTINGS

from .base import AndroidQFModule


class Settings(AndroidQFModule):
    """This module analyse setting files"""

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        fast_mode: Optional[bool] = False,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[list] = None
    ) -> None:
        super().__init__(file_path=file_path, target_path=target_path,
                         results_path=results_path, fast_mode=fast_mode,
                         log=log, results=results)
        self.results = {}

    def run(self) -> None:
        for setting_file in self._get_files_by_pattern("*/settings_*.txt"):
            namespace = setting_file[setting_file.rfind("_")+1:-4]

            self.results[namespace] = {}

            with open(setting_file) as handle:
                for line in handle:
                    line = line.strip()
                    try:
                        key, value = line.split("=", 1)
                    except ValueError:
                        continue

                    try:
                        self.results[namespace][key] = value
                    except IndexError:
                        continue

                    for danger in ANDROID_DANGEROUS_SETTINGS:
                        if (danger["key"] == key
                                and danger["safe_value"] != value):
                            self.log.warning("Found suspicious setting \"%s = %s\" (%s)",
                                             key, value, danger["description"])
                            break

        self.log.info("Identified %d settings",
                      sum([len(val) for val in self.results.values()]))
