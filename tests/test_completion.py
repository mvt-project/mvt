# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from click.testing import CliRunner

from mvt.android.cli import cli as android_cli
from mvt.ios.cli import cli as ios_cli


class TestCompletionCommand:
    def test_completion_prints_instructions_by_default(self):
        runner = CliRunner()
        result = runner.invoke(ios_cli, ["completion"])

        assert result.exit_code == 0
        assert "Shell completion for mvt-ios" in result.output
        assert "mvt-ios completion bash > ~/.mvt-ios-complete.bash" in result.output
        assert "Mobile Verification Toolkit" not in result.output

    def test_completion_prints_bash_script(self):
        runner = CliRunner()
        result = runner.invoke(ios_cli, ["completion", "bash"])

        assert result.exit_code == 0
        assert "_MVT_IOS_COMPLETE=bash_complete" in result.output
        assert "complete -o nosort" in result.output
        assert "mvt-ios" in result.output
        assert "Mobile Verification Toolkit" not in result.output

    def test_completion_prints_fish_script(self):
        runner = CliRunner()
        result = runner.invoke(android_cli, ["completion", "fish"])

        assert result.exit_code == 0
        assert "_MVT_ANDROID_COMPLETE=fish_complete" in result.output
        assert "complete --no-files --command mvt-android" in result.output
        assert "Mobile Verification Toolkit" not in result.output

    def test_completion_install_updates_bashrc_once(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        runner = CliRunner()

        result = runner.invoke(ios_cli, ["completion", "bash", "--install"])
        assert result.exit_code == 0

        script_path = tmp_path / ".mvt-ios-complete.bash"
        bashrc_path = tmp_path / ".bashrc"
        assert script_path.exists()
        assert "_MVT_IOS_COMPLETE=bash_complete" in script_path.read_text(
            encoding="utf-8"
        )
        bashrc = bashrc_path.read_text(encoding="utf-8")
        assert "[ -f" in bashrc
        assert ".mvt-ios-complete.bash" in bashrc

        result = runner.invoke(ios_cli, ["completion", "bash", "--install"])
        assert result.exit_code == 0
        assert bashrc_path.read_text(encoding="utf-8") == bashrc

    def test_completion_install_fish_does_not_update_shell_rc(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("HOME", str(tmp_path))
        runner = CliRunner()

        result = runner.invoke(android_cli, ["completion", "fish", "--install"])

        assert result.exit_code == 0
        script_path = (
            tmp_path / ".config" / "fish" / "completions" / "mvt-android.fish"
        )
        assert script_path.exists()
        assert "_MVT_ANDROID_COMPLETE=fish_complete" in script_path.read_text(
            encoding="utf-8"
        )
        assert not (tmp_path / ".fishrc").exists()
