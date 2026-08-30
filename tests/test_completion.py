# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from click.testing import CliRunner

from mvt.android.cli import cli as android_cli
from mvt.cli import cli as mvt_cli
from mvt.ios.cli import cli as ios_cli


class TestCompletionCommand:
    def test_completion_prints_instructions_by_default(self):
        runner = CliRunner()
        result = runner.invoke(mvt_cli, ["completion"])

        assert result.exit_code == 0
        assert "Shell completion for mvt, mvt-ios and mvt-android" in result.output
        assert "mvt completion bash > ~/.mvt-complete.bash" in result.output
        assert "Mobile Verification Toolkit" not in result.output

    def test_completion_bash_script_covers_every_cli(self):
        runner = CliRunner()
        result = runner.invoke(mvt_cli, ["completion", "bash"])

        assert result.exit_code == 0
        assert "_MVT_COMPLETE=bash_complete" in result.output
        assert "_MVT_IOS_COMPLETE=bash_complete" in result.output
        assert "_MVT_ANDROID_COMPLETE=bash_complete" in result.output
        assert "complete -o nosort" in result.output
        assert "Mobile Verification Toolkit" not in result.output

    def test_completion_fish_script_covers_every_cli(self):
        runner = CliRunner()
        result = runner.invoke(mvt_cli, ["completion", "fish"])

        assert result.exit_code == 0
        assert "complete --no-files --command mvt-ios" in result.output
        assert "complete --no-files --command mvt-android" in result.output
        assert "complete --no-files --command mvt " in result.output
        assert "Mobile Verification Toolkit" not in result.output

    def test_completion_install_updates_bashrc_once(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        runner = CliRunner()

        result = runner.invoke(mvt_cli, ["completion", "bash", "--install"])
        assert result.exit_code == 0

        script_path = tmp_path / ".mvt-complete.bash"
        bashrc_path = tmp_path / ".bashrc"
        assert script_path.exists()
        script = script_path.read_text(encoding="utf-8")
        assert "_MVT_COMPLETE=bash_complete" in script
        assert "_MVT_IOS_COMPLETE=bash_complete" in script
        assert "_MVT_ANDROID_COMPLETE=bash_complete" in script
        bashrc = bashrc_path.read_text(encoding="utf-8")
        assert "[ -f" in bashrc
        assert ".mvt-complete.bash" in bashrc

        result = runner.invoke(mvt_cli, ["completion", "bash", "--install"])
        assert result.exit_code == 0
        assert bashrc_path.read_text(encoding="utf-8") == bashrc

    def test_completion_install_fish_does_not_update_shell_rc(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("HOME", str(tmp_path))
        runner = CliRunner()

        result = runner.invoke(mvt_cli, ["completion", "fish", "--install"])

        assert result.exit_code == 0
        script_path = tmp_path / ".config" / "fish" / "conf.d" / "mvt-completion.fish"
        assert script_path.exists()
        script = script_path.read_text(encoding="utf-8")
        assert "_MVT_COMPLETE=fish_complete" in script
        assert "_MVT_IOS_COMPLETE=fish_complete" in script
        assert "_MVT_ANDROID_COMPLETE=fish_complete" in script
        assert not (tmp_path / ".fishrc").exists()
        assert not (tmp_path / ".bashrc").exists()
        assert not (tmp_path / ".zshrc").exists()

    def test_completion_install_without_shell_is_a_usage_error(self):
        runner = CliRunner()
        result = runner.invoke(mvt_cli, ["completion", "--install"])

        assert result.exit_code == 2
        assert "A shell is required when using --install." in result.output

    def test_completion_is_not_a_command_of_the_platform_clis(self):
        runner = CliRunner()

        assert "completion" not in ios_cli.commands
        assert "completion" not in android_cli.commands
        assert runner.invoke(ios_cli, ["completion"]).exit_code == 2
        assert runner.invoke(android_cli, ["completion"]).exit_code == 2
