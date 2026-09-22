import io
import gzip
import logging
import random
import tarfile
from datetime import timedelta
from pathlib import Path

import pytest
from mvt.ios.cmd_check_sysdiagnose import CmdIOSCheckSysdiagnose
from mvt.ios.modules.sysdiagnose import SysdiagnoseExtraction


class SysdiagnoseTestModule(SysdiagnoseExtraction):
    supported_commands = (("ios", "check-sysdiagnose"),)

    def run(self):
        file_path = self._get_files_by_pattern("*/artifact.txt")[0]
        self.results = [
            {
                "content": self._get_file_content(file_path).decode("utf-8"),
                "timezone_offset": self._extract_timezone().utcoffset(None).seconds,
            }
        ]

    def check_indicators(self):
        pass

    def serialize(self, result):
        return None


def _create_sysdiagnose_folder(tmp_path):
    folder = tmp_path / "sysdiagnose"
    folder.mkdir()
    (folder / "artifact.txt").write_text("artifact", encoding="utf-8")
    (folder / "sysdiagnose.log").write_text(
        "sysdiagnose_2024.01.02_03-04-05+0200.tar.gz", encoding="utf-8"
    )
    (folder / "report.ips").write_text('{"bug_type": 210}\nbody', encoding="utf-8")
    (folder / "._artifact.txt").write_bytes(b"\x00\x05\x16\x07AppleDouble")
    return folder


def _create_sysdiagnose_archive(tmp_path, folder):
    archive_path = tmp_path / "sysdiagnose.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        for path in folder.iterdir():
            archive.add(path, arcname=f"sysdiagnose/{path.name}")
    return archive_path


def _test_module(command):
    (module,) = [m for m in command.executed if isinstance(m, SysdiagnoseTestModule)]
    return module


def _run_command(path):
    command = CmdIOSCheckSysdiagnose(
        target_path=str(path), custom_modules=[SysdiagnoseTestModule]
    )
    command.run()
    return command


def test_check_sysdiagnose_from_folder(tmp_path):
    command = _run_command(_create_sysdiagnose_folder(tmp_path))

    assert _test_module(command).results == [
        {"content": "artifact", "timezone_offset": timedelta(hours=2).seconds}
    ]
    assert _test_module(command).ips_files == [
        {"file_path": str(tmp_path / "sysdiagnose" / "report.ips"), "bug_type": 210}
    ]
    assert "sysdiagnose/._artifact.txt" not in command.sysdiagnose_files


def test_check_sysdiagnose_from_archive_closes_archive(tmp_path):
    folder = _create_sysdiagnose_folder(tmp_path)
    command = _run_command(_create_sysdiagnose_archive(tmp_path, folder))

    assert _test_module(command).results == [
        {"content": "artifact", "timezone_offset": timedelta(hours=2).seconds}
    ]
    assert _test_module(command).ips_files == [
        {
            "file_path": str(Path(command.extracted_sysdiagnose_path) / "report.ips"),
            "bug_type": 210,
        }
    ]
    assert command.sysdiagnose_archive is None
    assert "sysdiagnose/._artifact.txt" not in command.sysdiagnose_files
    assert command.archive_incomplete is False
    assert _test_module(command).sysdiagnose_archive_incomplete is False


def test_archive_is_extracted_once_and_unsafe_members_are_skipped(tmp_path):
    archive_path = tmp_path / "sysdiagnose.tar.gz"
    escaped_path = tmp_path / "escaped.txt"
    content = b"test content"
    member = tarfile.TarInfo("sysdiagnose/artifact.txt")
    member.size = len(content)

    with tarfile.open(archive_path, "w:gz") as archive:
        archive.addfile(member, io.BytesIO(content))
        escaped = tarfile.TarInfo(f"sysdiagnose/../../{escaped_path.name}")
        escaped.size = len(content)
        archive.addfile(escaped, io.BytesIO(content))
        link = tarfile.TarInfo("sysdiagnose/link")
        link.type = tarfile.SYMTYPE
        link.linkname = "/etc/hostname"
        archive.addfile(link)

    command = CmdIOSCheckSysdiagnose(target_path=str(archive_path))
    try:
        command.init()
        extracted_path = Path(command.extracted_sysdiagnose_path)
        assert (extracted_path / "artifact.txt").read_bytes() == content
        assert not escaped_path.exists()
        assert not (extracted_path / "link").exists()

        module = SysdiagnoseExtraction()
        command.module_init(module)
        assert module.tar is None
        assert module.parent_path == str(extracted_path.parent)
    finally:
        command.finish()

    assert not extracted_path.exists()


def _recovery_archive(tmp_path, damage, last_name="partial.ips"):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as archive:
        for name, data in (
            ("artifact.txt", b"artifact"),
            ("sysdiagnose.log", b"sysdiagnose_2024.01.02_03-04-05+0200.tar.gz"),
            ("complete.ips", b'{"bug_type": 210}\ncomplete'),
            (last_name, b'{"bug_type": 210}\n' + random.Random(42).randbytes(200_000)),
        ):
            member = tarfile.TarInfo(f"sysdiagnose/{name}")
            member.size = len(data)
            member.mtime = 1_700_000_000
            member.pax_headers = {"LIBARCHIVE.creationtime": "1600000000.5"}
            last_header = archive.offset
            archive.addfile(member, io.BytesIO(data))
    data = gzip.compress(raw.getvalue())
    if damage == "gzip-body":
        data = data[: len(data) // 2]
    elif damage == "tar-body":
        data = gzip.compress(raw.getvalue()[: last_header + 2000])
    elif damage == "tar-header":
        data = gzip.compress(raw.getvalue()[: last_header + 100])
    elif damage == "gzip-trailer":
        data = data[:-8]
    elif damage == "checksum":
        data = data[:-8] + bytes(x ^ 0xFF for x in data[-8:-4]) + data[-4:]
    path = tmp_path / "sysdiagnose.tar.gz"
    path.write_bytes(data)
    return path


@pytest.mark.parametrize("damage", ["gzip-body", "tar-body", "tar-header"])
def test_recovers_complete_members_and_excludes_partial_files(tmp_path, caplog, damage):
    path = _recovery_archive(tmp_path, damage)
    original = path.read_bytes()
    command = CmdIOSCheckSysdiagnose(target_path=str(path))
    try:
        with caplog.at_level(logging.WARNING):
            command.init()
        root = Path(command.extracted_sysdiagnose_path)
        assert {p.name for p in root.iterdir()} == {
            "artifact.txt",
            "sysdiagnose.log",
            "complete.ips",
        }
        assert (root / "artifact.txt").read_bytes() == b"artifact"
        assert command.sysdiagnose_files == [
            "sysdiagnose/artifact.txt",
            "sysdiagnose/sysdiagnose.log",
            "sysdiagnose/complete.ips",
        ]
        assert [r["file_path"] for r in command.ips_files] == [
            str(root / "complete.ips")
        ]
        assert [
            m.name for m in command.sysdiagnose_tar_members
        ] == command.sysdiagnose_files
        assert (
            command.sysdiagnose_tar_members[0].pax_headers["LIBARCHIVE.creationtime"]
            == "1600000000.5"
        )
        assert command.archive_incomplete
        assert "truncated or damaged" in caplog.text
        assert "Recovered 3 complete files" in caplog.text
        assert "Analysis will be partial" in caplog.text
        assert path.read_bytes() == original
    finally:
        command.finish()
    assert not root.exists()


@pytest.mark.parametrize("damage", ["gzip-trailer", "checksum"])
def test_warns_when_tar_is_complete_but_gzip_integrity_fails(tmp_path, caplog, damage):
    path = _recovery_archive(tmp_path, damage)
    with caplog.at_level(logging.WARNING):
        command = _run_command(path)
    assert _test_module(command).results[0]["content"] == "artifact"
    assert command.archive_incomplete
    assert _test_module(command).sysdiagnose_archive_incomplete
    assert len(command.sysdiagnose_files) == 4
    assert "archive integrity cannot be verified" in caplog.text


def test_truncated_duplicate_preserves_earlier_complete_file(tmp_path):
    path = _recovery_archive(tmp_path, "gzip-body", last_name="artifact.txt")
    command = _run_command(path)
    assert _test_module(command).results[0]["content"] == "artifact"
    assert command.sysdiagnose_files.count("sysdiagnose/artifact.txt") == 1


def test_output_write_error_is_fatal_not_recovered(tmp_path, monkeypatch, caplog):
    path = _recovery_archive(tmp_path, "none")
    command = CmdIOSCheckSysdiagnose(target_path=str(path))

    def fail_copy(*args):
        raise OSError("disk full")

    monkeypatch.setattr("mvt.ios.cmd_check_sysdiagnose.shutil.copyfileobj", fail_copy)
    with pytest.raises(SystemExit) as error:
        command.init()
    assert error.value.code == 1
    assert not command.archive_incomplete
    assert "disk full" in caplog.text
    assert command.temp_sysdiagnose_dir is None
    assert command.sysdiagnose_archive is None


@pytest.mark.parametrize("offset", ["+0200", "-0530"])
def test_recovered_timezone_falls_back_to_original_filename(tmp_path, offset):
    path = _recovery_archive(tmp_path, "gzip-body")
    renamed = path.with_name(
        f"sysdiagnose_2026.09.14_20-04-52{offset}_iPhone-OS_iPhone_24A000.tar.gz"
    )
    path.rename(renamed)
    command = CmdIOSCheckSysdiagnose(target_path=str(renamed))
    try:
        command.init()
        module = SysdiagnoseExtraction(target_path=str(renamed))
        command.module_init(module)
        # Simulate the diagnostic log being in the missing part of an archive.
        module.files = [f for f in module.files if not f.endswith("/sysdiagnose.log")]
        expected = (
            timedelta(hours=2) if offset == "+0200" else -timedelta(hours=5, minutes=30)
        )
        assert module._extract_timezone().utcoffset(None) == expected
    finally:
        command.finish()


def test_recovery_still_skips_unsafe_paths_and_links(tmp_path):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as archive:
        for name in ("sysdiagnose/artifact.txt", "sysdiagnose/../../escaped.txt"):
            member = tarfile.TarInfo(name)
            member.size = 8
            archive.addfile(member, io.BytesIO(b"artifact"))
        link = tarfile.TarInfo("sysdiagnose/link")
        link.type = tarfile.SYMTYPE
        link.linkname = "/etc/hostname"
        archive.addfile(link)
    path = tmp_path / "sysdiagnose.tar.gz"
    path.write_bytes(gzip.compress(raw.getvalue())[:-8])
    command = CmdIOSCheckSysdiagnose(target_path=str(path))
    try:
        command.init()
        root = Path(command.extracted_sysdiagnose_path)
        assert {p.name for p in root.iterdir()} == {"artifact.txt"}
        assert command.sysdiagnose_files == ["sysdiagnose/artifact.txt"]
        assert [
            m.name for m in command.sysdiagnose_tar_members
        ] == command.sysdiagnose_files
        assert not (root.parent.parent / "escaped.txt").exists()
        assert command.archive_incomplete
    finally:
        command.finish()
