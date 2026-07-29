# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import gzip
import logging
import zipfile

from mvt.android.modules.androidqf.samsung_sfs_logs import SamsungSFSLogs
from mvt.common.module import run_module

from ..utils import list_files


SFS_LOG = """\
25-06-18 (GMT-03:00) 18:09:15.139 1498 D AdbDebuggingManager: Logging key QUJDRA== host@example, state = 2, alwaysAllow = true, lastConnectionTime = 0, authWindow = 604800000
25-06-18 (GMT-03:00) 18:10:00.000 1498 D UsbHostManager: USB device attached: vidpid 18d1:4ee7 mfg/product/ver/serial Google/Pixel/1.00/ABC123 hasAudio/HID/Storage: true/false/true
25-06-18 (GMT-03:00) 18:10:01.000 1498 V UsbDeviceManager: USB UEVENT: {SUBSYSTEM=android_usb, SEQNUM=42, ACTION=change, USB_STATE=CONFIGURED, DEVPATH=/devices/test}
malformed line
"""


def test_parse_samsung_sfs_log_from_directory(tmp_path):
    data_path = tmp_path / "androidqf"
    log_path = data_path / "logs" / "data" / "log" / "sfslog.0.gz"
    log_path.parent.mkdir(parents=True)
    log_path.write_bytes(gzip.compress(SFS_LOG.encode()))

    module = SamsungSFSLogs(target_path=str(data_path), log=logging)
    module.from_dir(
        str(data_path.parent),
        list_files(str(data_path)),
    )
    run_module(module)

    assert len(module.results) == 3
    assert len(module.timeline) == 3

    adb_result, device_result, state_result = module.results
    assert adb_result == {
        "timestamp": "2025-06-18 21:09:15.139000",
        "event": "adb_connection",
        "key": "QUJDRA==",
        "user": "host@example",
        "fingerprint": "CB:08:CA:4A:7B:B5:F9:68:3C:19:13:3A:84:87:2C:A7",
        "state": 2,
        "state_name": "user_allowed",
        "always_allow": True,
        "last_connection_time": 0,
        "auth_window": 604800000,
        "source_file": "androidqf/logs/data/log/sfslog.0.gz",
    }
    assert device_result["event"] == "usb_device_attached"
    assert device_result["vendor_id"] == "18d1"
    assert device_result["product_id"] == "4ee7"
    assert device_result["serial"] == "ABC123"
    assert device_result["has_audio"] is True
    assert device_result["has_hid"] is False
    assert device_result["has_storage"] is True
    assert state_result["event"] == "usb_state"
    assert state_result["usb_state"] == "CONFIGURED"
    assert state_result["sequence_number"] == "42"
    assert state_result["device_path"] == "/devices/test"


def test_parse_samsung_sfs_log_from_zip(tmp_path):
    archive_path = tmp_path / "androidqf.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "androidqf/logs/data/log/sfslog.1.gz",
            gzip.compress(SFS_LOG.encode()),
        )

    with zipfile.ZipFile(archive_path) as archive:
        module = SamsungSFSLogs(target_path=str(archive_path), log=logging)
        module.from_zip(archive, archive.namelist())
        run_module(module)

    assert len(module.results) == 3
    assert all(
        result["source_file"] == "androidqf/logs/data/log/sfslog.1.gz"
        for result in module.results
    )


def test_invalid_samsung_sfs_log_is_skipped(tmp_path, caplog):
    data_path = tmp_path / "androidqf"
    log_path = data_path / "logs" / "data" / "log" / "sfslog.0.gz"
    log_path.parent.mkdir(parents=True)
    log_path.write_text("not gzip")

    module = SamsungSFSLogs(target_path=str(data_path), log=logging)
    module.from_dir(
        str(data_path.parent),
        list_files(str(data_path)),
    )
    run_module(module)

    assert module.results == []
    assert "Unable to read Samsung system framework log" in caplog.text
