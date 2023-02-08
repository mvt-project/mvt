# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 Claudio Guarnieri.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import fnmatch
import logging
import os
from typing import Optional

from mvt.common.module import MVTModule


class AndroidQFModule(MVTModule):
    """This class provides a base for all Android Data analysis modules."""

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

        self._path = target_path
        self._files = []

        for root, dirs, files in os.walk(target_path):
            for name in files:
                self._files.append(os.path.join(root, name))

    def _get_files_by_pattern(self, pattern):
        return fnmatch.filter(self._files, pattern)
