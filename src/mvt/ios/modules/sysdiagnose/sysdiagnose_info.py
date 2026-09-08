# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import json
import logging
import os
import plistlib
import re
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from mvt.common.module_types import ModuleResults
from mvt.common.utils import convert_datetime_to_iso
from mvt.ios.versions import (
    find_version_by_build,
    get_device_desc_from_id,
    is_ios_version_outdated,
)

from .base import SysdiagnoseExtraction

# The fields dumpsys prints in the remotectl dump state and the mobile
# activation request which are worth a log line of their own.
LOGGED_FIELDS = (
    "ProductName",
    "ProductType",
    "SerialNumber",
    "OSVersion",
    "RegionCode",
    "IMEI",
    "BuildVersion",
)


class SysdiagnoseInfo(SysdiagnoseExtraction):
    """Extract details about the device and the sysdiagnose itself.

    The fields come from four files of the archive: the remotectl dump state
    (product type, OS version, serial number, region and the rest of its
    Properties block), the mobile activation request (UDID, IMEI, MEID and the
    OS build), the App Store daemon database (the Apple account name and email)
    and sysdiagnose.log (the archive's original file name and creation time).

    Newer iOS versions no longer include the App Store daemon database in a
    sysdiagnose; it is still read for the analysis of older archives.
    """

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        module_options: Optional[dict] = None,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[ModuleResults] = None,
    ) -> None:
        super().__init__(
            file_path=file_path,
            target_path=target_path,
            results_path=results_path,
            module_options=module_options,
            log=log,
            results=results,
        )

        self.results: dict = results if results is not None else {}

    def _copy_sqlite_db(self, file_path: str, directory: str) -> str:
        """Copy a database and its WAL sidecars out of the archive.

        A database dumped mid-transaction keeps its latest rows in the -wal
        file next to it, which SQLite only reads when both sit in the same
        directory under the same name.
        """
        available_files = self.tar_files if self.tar else self.files
        for suffix in ("", "-wal", "-shm"):
            if suffix and f"{file_path}{suffix}" not in available_files:
                continue
            copy_path = os.path.join(directory, f"{Path(file_path).name}{suffix}")
            with open(copy_path, "wb") as handle:
                handle.write(self._get_file_content(f"{file_path}{suffix}"))

        return os.path.join(directory, Path(file_path).name)

    def _process_appstored(self, file_path: str) -> None:
        self.log.info("Found App Store daemon database at: %s", file_path)
        with tempfile.TemporaryDirectory(prefix="mvt_sqlite_") as directory:
            db_path = Path(self._copy_sqlite_db(file_path, directory)).resolve()
            conn = sqlite3.connect(f"{db_path.as_uri()}?mode=ro", uri=True)
            try:
                self._read_appstored(conn)
            finally:
                conn.close()

    def _read_appstored(self, conn: sqlite3.Connection) -> None:
        cur = conn.cursor()
        # The account name sits in an opaque structure of every asset row.
        try:
            rows = cur.execute("SELECT sinfs_data FROM asset;").fetchall()
        except sqlite3.DatabaseError as exc:
            self.log.debug("Unable to read the asset table: %s", exc)
            rows = []

        for (sinfs_data,) in rows:
            try:
                sinf = plistlib.loads(sinfs_data)[0]["sinf"]
            except (plistlib.InvalidFileException, IndexError, KeyError, TypeError):
                continue
            match = re.search(rb"name(.*?)\x00", sinf)
            if match:
                self.results["Account Name"] = match.group(1).decode(
                    "utf-8", errors="replace"
                )
                break

        try:
            row = cur.execute(
                "SELECT store_account_name FROM job_software "
                "WHERE store_account_name IS NOT NULL LIMIT 1;"
            ).fetchone()
        except sqlite3.DatabaseError as exc:
            self.log.debug("Unable to read the job_software table: %s", exc)
            return

        if row:
            self.results["Email Address"] = row[0]

    def _process_activation_log(self, file_path: str) -> None:
        self.log.info("Found mobile activation request at: %s", file_path)
        content = self._get_file_content(file_path)
        match = re.search(rb"BODY:\s+({.+?})\s", content, re.MULTILINE)
        if not match:
            return

        try:
            body = json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            self.log.warning("Unable to parse the activation request body: %s", exc)
            return

        self.results.update(
            {
                "SerialNumber": body.get("serial-number"),
                "ProductType": body.get("productType"),
                "ProductName": body.get("productName"),
                "IMEI": body.get("imei"),
                "ProductVersion": body.get("os-version"),
                "UniqueIdentifier": body.get("udid"),
                "MEID": body.get("meid"),
                "BuildVersion": body.get("os-build"),
            }
        )

    def _process_dumpstate(self, file_path: str) -> None:
        self.log.info("Found remotectl dump state at: %s", file_path)
        content = self._get_file_content(file_path).decode("utf-8", errors="replace")
        in_properties = False
        for line in content.splitlines():
            if not in_properties:
                in_properties = line == "\tProperties: {"
                continue

            if line == "\t}":
                break

            key, separator, value = line.partition("=>")
            if separator:
                self.results[key.strip()] = value.strip()

    def _process_sysdiagnose_log(self, file_path: str) -> None:
        self.log.info("Found sysdiagnose.log at: %s", file_path)
        content = self._get_file_content(file_path).decode("utf-8", errors="replace")
        match = re.search(r"sysdiagnose_\S+?\.tar\.gz", content)
        if not match:
            self.log.info("Could not find the original output path in sysdiagnose.log")
            return

        file_name = os.path.basename(match.group(0))
        try:
            created = datetime.strptime(
                "_".join(file_name.split("_")[1:3]), "%Y.%m.%d_%H-%M-%S%z"
            )
        except ValueError:
            self.log.warning("Unexpected sysdiagnose file name: %s", file_name)
            return

        self.results["OriginalFilename"] = file_name
        self.results["CreatedTimestamp"] = convert_datetime_to_iso(created)

    def run(self) -> None:
        for file_path in self._get_files_by_pattern(
            "*/logs/appinstallation/appstored.sqlitedb"
        ):
            self._process_appstored(file_path)

        for file_path in self._get_files_by_pattern(
            "*/logs/MobileActivation/collection_oob_request.txt"
        ):
            self._process_activation_log(file_path)

        for file_path in self._get_files_by_pattern("*/remotectl_dumpstate.txt"):
            self._process_dumpstate(file_path)

        for file_path in self._get_files_by_pattern("*/sysdiagnose.log"):
            self._process_sysdiagnose_log(file_path)

        # The activation request names the product "iPhone OS"; the model
        # description is what an analyst wants to read.
        product_name = get_device_desc_from_id(self.results.get("ProductType", ""))
        if product_name:
            self.results["ProductName"] = product_name

        for field in LOGGED_FIELDS:
            if field not in self.results:
                continue
            value = self.results[field]
            if field == "BuildVersion" and value:
                self.log.info("%s: %s - %s", field, value, find_version_by_build(value))
            else:
                self.log.info("%s: %s", field, value)

        if self.results.get("BuildVersion"):
            is_ios_version_outdated(self.results["BuildVersion"], self.log)
