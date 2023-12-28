# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import glob
import logging
import os
import shutil
import sqlite3
import subprocess
from typing import Iterator, Optional, Union

from mvt.common.module import DatabaseCorruptedError, DatabaseNotFoundError, MVTModule


class IOSExtraction(MVTModule):
    """This class provides a base for all iOS filesystem/backup extraction
    modules."""

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        module_options: Optional[dict] = None,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[list] = None,
    ) -> None:
        super().__init__(
            file_path=file_path,
            target_path=target_path,
            results_path=results_path,
            module_options=module_options,
            log=log,
            results=results,
        )

        self.is_backup = False
        self.is_fs_dump = False

    def _recover_sqlite_db_if_needed(
        self, file_path: str, forced: bool = False
    ) -> None:
        """Tries to recover a malformed database by running a .clone command.

        :param file_path: Path to the malformed database file.

        """
        # TODO: Find a better solution.
        if not forced:
            conn = self._open_sqlite_db(file_path)
            cur = conn.cursor()

            try:
                recover = False
                cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            except sqlite3.DatabaseError as exc:
                if "database disk image is malformed" in str(exc):
                    recover = True
            finally:
                conn.close()

            if not recover:
                return

        self.log.info(
            "Database at path %s is malformed. Trying to recover...", file_path
        )

        if not shutil.which("sqlite3"):
            raise DatabaseCorruptedError(
                "failed to recover without sqlite3 binary: please install " "sqlite3!"
            )
        if '"' in file_path:
            raise DatabaseCorruptedError(
                f"database at path '{file_path}' is corrupted. unable to "
                'recover because it has a quotation mark (") in its name'
            )

        bak_path = f"{file_path}.bak"
        shutil.move(file_path, bak_path)

        ret = subprocess.call(
            ["sqlite3", bak_path, f'.clone "{file_path}"'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if ret != 0:
            raise DatabaseCorruptedError("failed to recover database")

        self.log.info("Database at path %s recovered successfully!", file_path)

    def _open_sqlite_db(self, file_path: str) -> sqlite3.Connection:
        return sqlite3.connect(f"file:{file_path}?immutable=1", uri=True)

    def _get_backup_files_from_manifest(
        self, relative_path: Optional[str] = None, domain: Optional[str] = None
    ) -> Iterator[dict]:
        """Locate files from Manifest.db.

        :param relative_path: Relative path to use as filter from Manifest.db.
                              (Default value = None)
        :param domain: Domain to use as filter from Manifest.db.
                       (Default value = None)

        """
        manifest_db_path = os.path.join(self.target_path, "Manifest.db")
        if not os.path.exists(manifest_db_path):
            raise DatabaseNotFoundError("unable to find backup's Manifest.db")

        base_sql = "SELECT fileID, domain, relativePath FROM Files WHERE "

        try:
            conn = self._open_sqlite_db(manifest_db_path)
            cur = conn.cursor()
            if relative_path and domain:
                cur.execute(
                    f"{base_sql} relativePath = ? AND domain = ?;",
                    (relative_path, domain),
                )
            else:
                if relative_path:
                    if "*" in relative_path:
                        cur.execute(
                            f"{base_sql} relativePath LIKE ?;",
                            (relative_path.replace("*", "%"),),
                        )
                    else:
                        cur.execute(f"{base_sql} relativePath = ?;", (relative_path,))
                elif domain:
                    cur.execute(f"{base_sql} domain = ?;", (domain,))
        except Exception as exc:
            raise DatabaseCorruptedError(f"failed to query Manifest.db: {exc}") from exc

        for row in cur:
            yield {
                "file_id": row[0],
                "domain": row[1],
                "relative_path": row[2],
            }

    def _get_backup_file_from_id(self, file_id: str) -> Union[str, None]:
        file_path = os.path.join(self.target_path, file_id[0:2], file_id)
        if os.path.exists(file_path):
            return file_path

        return None

    def _get_fs_files_from_patterns(self, root_paths: list) -> Iterator[str]:
        for root_path in root_paths:
            for found_path in glob.glob(os.path.join(self.target_path, root_path)):
                if not os.path.exists(found_path):
                    continue

                yield found_path

    def _find_ios_database(
        self, backup_ids: Optional[list] = None, root_paths: Optional[list] = None
    ) -> None:
        """Try to locate a module's database file from either an iTunes
        backup or a full filesystem dump. This is intended only for
        modules that expect to work with a single SQLite database.
        If a module requires to process multiple databases or files,
        you should use the helper functions above.

        :param root_paths: Glob patterns for files to seek in filesystem dump.
                           (Default value = [])
        :param backup_ids: Default value = None)

        """
        file_path = None
        # First we check if the was an explicit file path specified.
        if not self.file_path:
            # If not, we first try with backups.
            # We construct the path to the file according to the iTunes backup
            # folder structure, if we have a valid ID.
            if backup_ids:
                for backup_id in backup_ids:
                    file_path = self._get_backup_file_from_id(backup_id)
                    if file_path:
                        break

            if root_paths:
                # If this file does not exist we might be processing a full
                # filesystem dump (checkra1n all the things!).
                if not file_path or not os.path.exists(file_path):
                    # We reset the file_path.
                    file_path = None
                    for found_path in self._get_fs_files_from_patterns(root_paths):
                        file_path = found_path
                        break

        # If we do not find any, we fail.
        if file_path:
            self.file_path = file_path
        else:
            raise DatabaseNotFoundError("unable to find the module's database file")

        self._recover_sqlite_db_if_needed(self.file_path)
