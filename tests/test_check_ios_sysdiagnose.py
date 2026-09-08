import logging
import os
import tarfile

from click.testing import CliRunner

from mvt.ios.cli import check_sysdiagnose


CUSTOM_MODULE = """
from mvt.ios.modules.sysdiagnose import SysdiagnoseExtraction


class CustomSysdiagnoseModule(SysdiagnoseExtraction):
    supported_commands = (("ios", "check-sysdiagnose"),)
    slug = "custom_sysdiagnose_module"

    def run(self):
        file_path = self._get_files_by_pattern("*/artifact.txt")[0]
        self.results = [{"content": self._get_file_content(file_path).decode("utf-8")}]

    def check_indicators(self):
        pass

    def serialize(self, result):
        return None
"""


def _create_sysdiagnose_folder(tmp_path):
    folder = tmp_path / "sysdiagnose"
    folder.mkdir()
    (folder / "artifact.txt").write_text("artifact", encoding="utf-8")
    return folder


def test_check_sysdiagnose_runs_explicitly_scoped_custom_module(tmp_path):
    module_path = tmp_path / "custom_sysdiagnose.py"
    module_path.write_text(CUSTOM_MODULE, encoding="utf-8")
    output_path = tmp_path / "output"

    result = CliRunner().invoke(
        check_sysdiagnose,
        [
            "--load-module",
            str(module_path),
            "--output",
            str(output_path),
            str(_create_sysdiagnose_folder(tmp_path)),
        ],
    )

    assert result.exit_code == 0
    assert (output_path / "custom_sysdiagnose_module.json").exists()


def test_check_sysdiagnose_warns_without_a_custom_module(tmp_path, caplog):
    # The built-in SysdiagnoseInfo alone performs no check, so the run goes
    # ahead but says so.
    with caplog.at_level(logging.WARNING, logger="mvt"):
        result = CliRunner().invoke(
            check_sysdiagnose, [str(_create_sysdiagnose_folder(tmp_path))]
        )

    assert result.exit_code == 0
    assert "No forensic sysdiagnose modules have been loaded" in caplog.text


def _create_truncated_sysdiagnose_archive(tmp_path):
    folder = tmp_path / "sysdiagnose_2026.01.01_00-00-00+0000_iPhone-OS_iPhone_23A000"
    folder.mkdir()
    (folder / "sysdiagnose.log").write_bytes(os.urandom(200_000))
    archive = tmp_path / "sysdiagnose.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(folder, arcname=folder.name)
    data = archive.read_bytes()
    archive.write_bytes(data[: len(data) // 2])
    return archive


def test_check_sysdiagnose_reports_a_truncated_archive(tmp_path, caplog):
    # A download that stopped halfway ends in EOFError from gzip, which Click
    # would otherwise turn into a bare "Aborted!" with no reason given.
    archive = _create_truncated_sysdiagnose_archive(tmp_path)

    with caplog.at_level(logging.CRITICAL, logger="mvt"):
        result = CliRunner().invoke(check_sysdiagnose, [str(archive)])

    assert result.exit_code == 1
    assert "Unable to read the sysdiagnose archive" in caplog.text
    assert "truncated" in caplog.text
    assert "Aborted!" not in result.output
