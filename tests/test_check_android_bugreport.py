# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import datetime
import logging
import os
import shutil
import zipfile

from click.testing import CliRunner

from mvt.android.cli import check_bugreport
from mvt.android.cmd_check_bugreport import CmdAndroidCheckBugreport

from .utils import get_artifact_folder


class TestCheckBugreportCommand:
    def test_check(self):
        runner = CliRunner()
        path = os.path.join(get_artifact_folder(), "android_data/bugreport/")
        result = runner.invoke(check_bugreport, [path])
        assert result.exit_code == 0

    def test_invalid_zip_reports_clean_error(self, tmp_path):
        path = tmp_path / "invalid.zip"
        path.write_bytes(b"not a zip archive")

        result = CliRunner().invoke(check_bugreport, [str(path)])

        assert result.exit_code == 1
        assert "Invalid bugreport archive" in result.output
        assert "Traceback" not in result.output


PROPERTIES = (
    "------ SYSTEM PROPERTIES (getprop) ------\n"
    "[persist.sys.timezone]: [Africa/Nairobi]\n"
    "------ 0.01s was the duration of 'SYSTEM PROPERTIES' ------\n"
)
TOMBSTONE = "android_data/bugreport/FS/data/tombstones/tombstone_00"


def _bugreport_zip(tmp_path, dumpstate=PROPERTIES):
    """A bugreport zip holding one tombstone written at 11:38:10 device time.

    An even second: zip entry times have a two-second resolution.
    """
    path = tmp_path / "bugreport.zip"
    with open(os.path.join(get_artifact_folder(), TOMBSTONE), "rb") as handle:
        tombstone = handle.read()
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("main_entry.txt", "dumpstate.txt")
        archive.writestr("dumpstate.txt", dumpstate)
        entry = zipfile.ZipInfo(
            "FS/data/tombstones/tombstone_00", date_time=(2023, 3, 10, 11, 38, 10)
        )
        archive.writestr(entry, tombstone)
    return str(path)


def _tombstone_timestamp(target, **options):
    cmd = CmdAndroidCheckBugreport(
        target_path=target,
        module_name="Tombstones",
        disable_version_check=True,
        disable_indicator_check=True,
        **options,
    )
    cmd.run()
    return cmd, cmd.executed[0].results[0]["file_timestamp"]


class TestCheckBugreportTimezone:
    def test_zip_entry_times_are_read_in_the_device_timezone(self, tmp_path):
        cmd, file_timestamp = _tombstone_timestamp(_bugreport_zip(tmp_path))

        assert cmd.module_options["device_timezone"] == "Africa/Nairobi"
        # 11:38:10 in Nairobi is 08:38:10 UTC.
        assert file_timestamp == "2023-03-10 08:38:10.000000"

    def test_timezone_option_wins_over_the_bugreport(self, tmp_path):
        _, file_timestamp = _tombstone_timestamp(
            _bugreport_zip(tmp_path), module_options={"device_timezone": "Europe/Paris"}
        )

        assert file_timestamp == "2023-03-10 10:38:10.000000"

        result = CliRunner().invoke(
            check_bugreport,
            ["-t", "Europe/Paris", "-m", "Tombstones", _bugreport_zip(tmp_path)],
        )
        assert result.exit_code == 0, result.output

    def test_without_a_timezone_the_wall_clock_is_kept_and_a_warning_given(
        self, tmp_path, caplog
    ):
        with caplog.at_level(logging.WARNING, logger="mvt"):
            _, file_timestamp = _tombstone_timestamp(_bugreport_zip(tmp_path, ""))

        assert file_timestamp == "2023-03-10 11:38:10.000000"
        assert "persist.sys.timezone not found" in caplog.text

    def test_unpacked_bugreport_warns_and_reads_mtimes_as_utc(self, tmp_path, caplog):
        unpacked = tmp_path / "bugreport"
        shutil.copytree(
            os.path.join(get_artifact_folder(), "android_data/bugreport"), unpacked
        )
        instant = datetime.datetime(
            2023, 3, 10, 8, 38, 11, tzinfo=datetime.timezone.utc
        ).timestamp()
        for name in ("tombstone_00", "tombstone_01"):
            os.utime(unpacked / "FS" / "data" / "tombstones" / name, (instant, instant))

        with caplog.at_level(logging.WARNING, logger="mvt"):
            _, file_timestamp = _tombstone_timestamp(str(unpacked))

        assert "unpacked bugreport" in caplog.text
        # Whatever the zone of the machine running the analysis.
        assert file_timestamp == "2023-03-10 08:38:11.000000"
