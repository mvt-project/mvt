# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2022 The MVT Project Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import fnmatch
import os

from mvt.common.module import MVTModule


class BackupExtraction(MVTModule):
    """This class provides a base for all backup extractios modules"""
    ab = None

    def from_folder(self, backup_path, files):
        """
        Get all the files and list them
        """
        self.backup_path = backup_path
        self.files = files

    def from_ab(self, file_path, tar, files):
        """
        Extract the files
        """
        self.ab = file_path
        self.tar = tar
        self.files = files

    def _get_files_by_pattern(self, pattern):
        return fnmatch.filter(self.files, pattern)

    def _get_file_content(self, file_path):
        if self.ab:
            try:
                member = self.tar.getmember(file_path)
            except KeyError:
                return None
            handle = self.tar.extractfile(member)
        else:
            handle = open(os.path.join(self.backup_path, file_path), "rb")

        data = handle.read()
        handle.close()
        return data
