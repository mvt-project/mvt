# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 MVT Project Developers.
# See the file 'LICENSE' for usage and copying permissions, or find a copy at
#   https://github.com/mvt-project/mvt/blob/main/LICENSE

import os
import glob

from mvt.common.module import MVTModule

class IOSExtraction(MVTModule):
    """This class provides a base for all iOS filesystem/backup extraction modules."""

    is_backup = False
    is_fs_dump = False
    is_sysdiagnose = False

    def _find_ios_database(self, backup_ids=None, root_paths=[]):
        """Try to locate the module's database file from either an iTunes
        backup or a full filesystem dump.
        :param backup_id: iTunes backup database file's ID (or hash).
        """
        file_path = None
        # First we check if the was an explicit file path specified.
        if not self.file_path:
            # If not, we first try with backups.
            # We construct the path to the file according to the iTunes backup
            # folder structure, if we have a valid ID.
            if backup_ids:
                for backup_id in backup_ids:
                    file_path = os.path.join(self.base_folder, backup_id[0:2], backup_id)
                    # If we found the correct backup file, then we stop searching.
                    if os.path.exists(file_path):
                        break

            # If this file does not exist we might be processing a full
            # filesystem dump (checkra1n all the things!).
            if not file_path or not os.path.exists(file_path):
                # We reset the file_path.
                file_path = None
                for root_path in root_paths:
                    for found_path in glob.glob(os.path.join(self.base_folder, root_path)):
                        # If we find a valid path, we set file_path.
                        if os.path.exists(found_path):
                            file_path = found_path
                            break

                        # Otherwise, we reset the file_path again.
                        file_path = None

        # If we do not find any, we fail.
        if file_path:
            self.file_path = file_path
        else:
            raise FileNotFoundError("Unable to find the module's database file")
