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


def test_check_sysdiagnose_requires_an_explicitly_scoped_module(tmp_path):
    result = CliRunner().invoke(check_sysdiagnose, [str(_create_sysdiagnose_folder(tmp_path))])

    assert result.exit_code != 0
    assert "No custom modules support mvt-ios check-sysdiagnose" in result.output
