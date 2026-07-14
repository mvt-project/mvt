import tarfile
from datetime import timedelta

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
    return folder


def _create_sysdiagnose_archive(tmp_path, folder):
    archive_path = tmp_path / "sysdiagnose.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        for path in folder.iterdir():
            archive.add(path, arcname=f"sysdiagnose/{path.name}")
    return archive_path


def _run_command(path):
    command = CmdIOSCheckSysdiagnose(
        target_path=str(path), custom_modules=[SysdiagnoseTestModule]
    )
    command.run()
    return command


def test_check_sysdiagnose_from_folder(tmp_path):
    command = _run_command(_create_sysdiagnose_folder(tmp_path))

    assert command.executed[0].results == [
        {"content": "artifact", "timezone_offset": timedelta(hours=2).seconds}
    ]
    assert command.executed[0].ips_files == [
        {"file_path": str(tmp_path / "sysdiagnose" / "report.ips"), "bug_type": 210}
    ]


def test_check_sysdiagnose_from_archive_closes_archive(tmp_path):
    folder = _create_sysdiagnose_folder(tmp_path)
    command = _run_command(_create_sysdiagnose_archive(tmp_path, folder))

    assert command.executed[0].results == [
        {"content": "artifact", "timezone_offset": timedelta(hours=2).seconds}
    ]
    assert command.executed[0].ips_files == [
        {"file_path": "sysdiagnose/report.ips", "bug_type": 210}
    ]
    assert command.sysdiagnose_archive is None
