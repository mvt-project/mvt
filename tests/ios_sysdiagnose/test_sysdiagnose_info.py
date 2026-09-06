# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import json
import plistlib
import sqlite3
import tarfile

from mvt.common.module import run_module
from mvt.ios.cmd_check_sysdiagnose import CmdIOSCheckSysdiagnose
from mvt.ios.modules.sysdiagnose.sysdiagnose_info import SysdiagnoseInfo
from mvt.ios.versions import get_device_desc_from_id

# The name sysdiagnose gives its archive: the time it ran, then the OS and build.
ARCHIVE_NAME = "sysdiagnose_2024.01.02_03-04-05+0200_iPhone-OS_iPhone_21C62"

DUMPSTATE = (
    "Found device: ...\n"
    "\tProperties: {\n"
    "\t\tProductType => iPhone12,1\n"
    "\t\tOSVersion => 17.2\n"
    "\t\tSerialNumber => C0FFEE000000\n"
    "\t\tRegionCode => LL\n"
    "\t}\n"
    "\tServices: {\n"
    "\t\tcom.apple.example => ignored\n"
    "\t}\n"
)

ACTIVATION_BODY = {
    "serial-number": "C0FFEE000000",
    "productType": "iPhone12,1",
    "productName": "iPhone OS",
    "imei": "000000000000000",
    "os-version": "17.2",
    "os-build": "21C62",
    "udid": "00000000-0000000000000000",
    "meid": "00000000000000",
}


def make_sysdiagnose(tmp_path, activation_body=None):
    folder = tmp_path / ARCHIVE_NAME
    folder.mkdir()
    (folder / "sysdiagnose.log").write_text(
        f"Output available at '/private/var/tmp/{ARCHIVE_NAME}.tar.gz'\n",
        encoding="utf-8",
    )
    (folder / "remotectl_dumpstate.txt").write_text(DUMPSTATE, encoding="utf-8")

    activation = folder / "logs" / "MobileActivation"
    activation.mkdir(parents=True)
    body = json.dumps(
        activation_body if activation_body is not None else ACTIVATION_BODY
    )
    (activation / "collection_oob_request.txt").write_text(
        f"HEADERS: {{}}\nBODY: {body}\nEND\n", encoding="utf-8"
    )

    appinstallation = folder / "logs" / "appinstallation"
    appinstallation.mkdir(parents=True)
    conn = sqlite3.connect(appinstallation / "appstored.sqlitedb")
    conn.execute("CREATE TABLE asset (sinfs_data BLOB)")
    conn.execute(
        "INSERT INTO asset VALUES (?)",
        (plistlib.dumps([{"sinf": b"\x00\x10nameExample Person\x00\x00rest"}]),),
    )
    conn.execute("CREATE TABLE job_software (store_account_name TEXT)")
    conn.execute("INSERT INTO job_software VALUES (NULL)")
    conn.execute("INSERT INTO job_software VALUES ('person@example.com')")
    conn.commit()
    conn.close()
    return folder


def run_command(target, results_path=None):
    command = CmdIOSCheckSysdiagnose(target_path=str(target), results_path=results_path)
    command.run()
    (module,) = [m for m in command.executed if isinstance(m, SysdiagnoseInfo)]
    return module


def test_device_details_from_a_sysdiagnose_folder(tmp_path):
    results_path = tmp_path / "results"
    results_path.mkdir()
    module = run_command(make_sysdiagnose(tmp_path), str(results_path))

    assert module.results["SerialNumber"] == "C0FFEE000000"
    assert module.results["ProductType"] == "iPhone12,1"
    assert module.results["ProductName"] == get_device_desc_from_id("iPhone12,1")
    assert module.results["ProductName"] != "iPhone OS"
    assert module.results["OSVersion"] == "17.2"
    assert module.results["BuildVersion"] == "21C62"
    assert module.results["UniqueIdentifier"] == "00000000-0000000000000000"
    assert module.results["RegionCode"] == "LL"
    assert "com.apple.example" not in module.results
    assert module.results["Account Name"] == "Example Person"
    assert module.results["Email Address"] == "person@example.com"
    assert module.results["OriginalFilename"] == f"{ARCHIVE_NAME}.tar.gz"
    assert module.results["CreatedTimestamp"] == "2024-01-02 01:04:05.000000"
    assert (results_path / "sysdiagnose_info.json").exists()


def test_device_details_from_a_sysdiagnose_archive(tmp_path):
    folder = make_sysdiagnose(tmp_path)
    archive_path = tmp_path / f"{ARCHIVE_NAME}.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(folder, arcname=ARCHIVE_NAME)

    module = run_command(archive_path)

    assert module.results["SerialNumber"] == "C0FFEE000000"
    assert module.results["Account Name"] == "Example Person"
    assert module.results["OriginalFilename"] == f"{ARCHIVE_NAME}.tar.gz"


def test_wal_sidecars_are_copied_beside_the_database(tmp_path):
    folder = tmp_path / ARCHIVE_NAME
    (folder / "logs").mkdir(parents=True)
    (folder / "logs" / "db.sqlite").write_bytes(b"main")
    (folder / "logs" / "db.sqlite-wal").write_bytes(b"wal")
    module = SysdiagnoseInfo()
    module.from_sysdiagnose_folder(
        str(folder),
        [f"{ARCHIVE_NAME}/logs/db.sqlite", f"{ARCHIVE_NAME}/logs/db.sqlite-wal"],
    )
    copies = tmp_path / "copies"
    copies.mkdir()

    db_path = module._copy_sqlite_db(f"{ARCHIVE_NAME}/logs/db.sqlite", str(copies))

    assert db_path == str(copies / "db.sqlite")
    assert (copies / "db.sqlite").read_bytes() == b"main"
    assert (copies / "db.sqlite-wal").read_bytes() == b"wal"
    assert not (copies / "db.sqlite-shm").exists()


def test_a_sysdiagnose_without_the_files_yields_nothing(tmp_path):
    folder = tmp_path / ARCHIVE_NAME
    folder.mkdir()
    (folder / "other.txt").write_text("nothing here", encoding="utf-8")

    module = SysdiagnoseInfo()
    module.from_sysdiagnose_folder(str(folder), [f"{ARCHIVE_NAME}/other.txt"])
    run_module(module)

    assert module.results == {}


def test_a_malformed_activation_request_is_skipped(tmp_path):
    folder = make_sysdiagnose(tmp_path)
    (folder / "logs" / "MobileActivation" / "collection_oob_request.txt").write_text(
        "BODY: {not json}\n", encoding="utf-8"
    )

    module = run_command(folder)

    assert "IMEI" not in module.results
    assert module.results["SerialNumber"] == "C0FFEE000000"
