# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/
"""An OEM wrapper archive must not read as an empty bug report.

MIUI / HyperOS hands out a zip of app logs with the real
`bugreport-<device>-<timestamp>.zip` nested inside. The outer archive has
none of the entry points the modules read, so every module
reported it found nothing and the command still exited 0 — an empty analysis
that looks like a finished one.
"""

import io
import zipfile

from mvt.android.cmd_check_bugreport import CmdAndroidCheckBugreport

DUMPSTATE = "== dumpstate: 2026-01-01 00:00:00\nDUMP OF SERVICE package:\n"


def _inner_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as inner:
        inner.writestr("main_entry.txt", "bugreport-test-2026-01-01-00-00-00.txt")
        inner.writestr("bugreport-test-2026-01-01-00-00-00.txt", DUMPSTATE)
    return buffer.getvalue()


def _wrapper_zip() -> zipfile.ZipFile:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as outer:
        outer.writestr("app_logs/hilog.txt", "unrelated OEM log\n")
        outer.writestr("bugreport-test-2026-01-01-00-00-00.zip", _inner_zip())
    return zipfile.ZipFile(io.BytesIO(buffer.getvalue()))


class TestCheckBugreportWrapper:
    def test_nested_bugreport_is_used(self, tmp_path):
        cmd = CmdAndroidCheckBugreport(results_path=str(tmp_path))
        cmd.from_zip(_wrapper_zip())
        module = cmd.modules[0](results_path=str(tmp_path))
        cmd.module_init(module)
        assert "main_entry.txt" in module.zip_files

    def test_plain_bugreport_is_left_alone(self, tmp_path):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("main_entry.txt", "bugreport.txt")
            archive.writestr("bugreport.txt", DUMPSTATE)
            archive.writestr("attachments/extra.zip", _inner_zip())
        cmd = CmdAndroidCheckBugreport(results_path=str(tmp_path))
        cmd.from_zip(zipfile.ZipFile(io.BytesIO(buffer.getvalue())))
        module = cmd.modules[0](results_path=str(tmp_path))
        cmd.module_init(module)
        assert "attachments/extra.zip" in module.zip_files
