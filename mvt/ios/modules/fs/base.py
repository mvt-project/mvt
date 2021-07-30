# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 MVT Project Developers.
# See the file 'LICENSE' for usage and copying permissions, or find a copy at
#   https://github.com/mvt-project/mvt/blob/main/LICENSE

import glob
import io
import os
import shutil
import sqlite3
import subprocess

from mvt.common.module import (DatabaseCorruptedError, DatabaseNotFoundError,
                               MVTModule)


class IOSExtraction(MVTModule):
    """This class provides a base for all iOS filesystem/backup extraction modules."""

    is_backup = False
    is_fs_dump = False
    is_sysdiagnose = False

    def _is_database_malformed(self, file_path):
        # Check if the database is malformed.
        conn = sqlite3.connect(file_path)
        cur = conn.cursor()

        try:
            recover = False
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        except sqlite3.DatabaseError as e:
            if "database disk image is malformed" in str(e):
                recover = True
        finally:
            conn.close()

        return recover

    def _recover_database(self, file_path):
        """Tries to recover a malformed database by running a .clone command.
        :param file_path: Path to the malformed database file.
        """
        # TODO: Find a better solution.

        self.log.info("Database at path %s is malformed. Trying to recover...", file_path)

        if not os.path.exists(file_path):
            return

        if not shutil.which("sqlite3"):
            raise DatabaseCorruptedError("Unable to recover without sqlite3 binary. Please install sqlite3!")

        bak_path = f"{file_path}.bak"
        shutil.move(file_path, bak_path)

        cmd = f"sqlite3 {bak_path} '.clone {file_path}'"
        ret = subprocess.call(cmd, shell=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        if ret != 0:
            raise DatabaseCorruptedError("Recovery of database failed")

        self.log.info("Database at path %s recovered successfully!", file_path)

    def _find_ios_database(self, backup_ids=None, root_paths=[]):
        """Try to locate the module's database file from either an iTunes
        backup or a full filesystem dump.
        :param backup_id: iTunes backup database file's ID (or hash).
        :param root_paths: Glob patterns for files to seek in filesystem dump.
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
            raise DatabaseNotFoundError("Unable to find the module's database file")

        if self._is_database_malformed(self.file_path):
            self._recover_database(self.file_path)
