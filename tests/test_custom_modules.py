from click.testing import CliRunner

from mvt.android.cli import check_bugreport
from mvt.android.cmd_check_androidqf import CmdAndroidCheckAndroidQF
from mvt.android.cmd_check_backup import CmdAndroidCheckBackup
from mvt.android.cmd_check_bugreport import CmdAndroidCheckBugreport
from mvt.android.cmd_check_intrusion_logs import CmdAndroidCheckIntrusionLogs
from mvt.common.module import MVTModule
from mvt.ios.cli import check_backup, check_fs


CUSTOM_MODULE = """
from mvt.common.module import MVTModule


class {name}(MVTModule):
    supported_commands = {supported_commands!r}
    slug = "{slug}"

    def run(self):
        self.results = [{{"message": "custom module ran"}}]

    def check_indicators(self):
        pass

    def serialize(self, result):
        return None
"""


def _write_custom_module(path, name, supported_commands, slug=None):
    path.write_text(
        CUSTOM_MODULE.format(
            name=name,
            supported_commands=supported_commands,
            slug=slug or name.lower(),
        ),
        encoding="utf-8",
    )
    return path


def test_load_module_appears_only_for_supported_cli_command(tmp_path):
    module_path = _write_custom_module(
        tmp_path / "custom.py",
        "IOSBackupOnlyModule",
        (("ios", "check-backup"),),
    )

    backup_result = CliRunner().invoke(
        check_backup,
        ["--list-modules", "--load-module", str(module_path), str(tmp_path)],
    )
    fs_result = CliRunner().invoke(
        check_fs,
        ["--list-modules", "--load-module", str(module_path), str(tmp_path)],
    )

    assert backup_result.exit_code == 0
    assert "IOSBackupOnlyModule" in backup_result.output
    assert fs_result.exit_code == 0
    assert "IOSBackupOnlyModule" not in fs_result.output


def test_module_option_runs_supported_custom_module(tmp_path):
    module_path = _write_custom_module(
        tmp_path / "custom.py",
        "CustomRunModule",
        (("ios", "check-backup"),),
        slug="custom_run_module",
    )
    output_path = tmp_path / "out"

    result = CliRunner().invoke(
        check_backup,
        [
            "--module",
            "CustomRunModule",
            "--load-module",
            str(module_path),
            "--output",
            str(output_path),
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert (output_path / "custom_run_module.json").exists()


def test_custom_modules_load_from_environment_without_cli_flag(tmp_path, monkeypatch):
    custom_modules_path = tmp_path / "custom_modules"
    custom_modules_path.mkdir()
    _write_custom_module(
        custom_modules_path / "env_module.py",
        "EnvBugreportModule",
        (("android", "check-bugreport"),),
    )
    monkeypatch.setenv("MVT_CUSTOM_MODULES", str(custom_modules_path))

    result = CliRunner().invoke(check_bugreport, ["--list-modules", str(tmp_path)])

    assert result.exit_code == 0
    assert "EnvBugreportModule" in result.output


class NestedBugreportModule(MVTModule):
    supported_commands = (("android", "check-bugreport"),)


class NestedBackupModule(MVTModule):
    supported_commands = (("android", "check-backup"),)


class NestedIntrusionLogsModule(MVTModule):
    supported_commands = (("android", "check-intrusion-logs"),)


class NestedAndroidQFModule(MVTModule):
    supported_commands = (("android", "check-androidqf"),)


class DummyZip:
    def close(self):
        pass


def test_androidqf_propagates_custom_modules_to_nested_commands(tmp_path, monkeypatch):
    records = {}
    custom_modules = [
        NestedBugreportModule,
        NestedBackupModule,
        NestedIntrusionLogsModule,
        NestedAndroidQFModule,
    ]
    cmd = CmdAndroidCheckAndroidQF(
        target_path=str(tmp_path),
        custom_modules=custom_modules,
    )

    def record_available(name):
        def _record(command):
            records[name] = [
                module.__name__
                for module in command._available_modules()
                if module.__name__.startswith("Nested")
            ]

        return _record

    monkeypatch.setattr(cmd, "load_bugreport", lambda: DummyZip())
    monkeypatch.setattr(
        CmdAndroidCheckBugreport,
        "from_zip",
        lambda self, bugreport: None,
    )
    monkeypatch.setattr(
        CmdAndroidCheckBugreport,
        "run",
        record_available("bugreport"),
    )

    monkeypatch.setattr(cmd, "load_backup", lambda: b"")
    monkeypatch.setattr(CmdAndroidCheckBackup, "from_ab", lambda self, backup: None)
    monkeypatch.setattr(
        CmdAndroidCheckBackup,
        "run",
        record_available("backup"),
    )

    intrusion_logs_path = tmp_path / "intrusion_logs"
    intrusion_logs_path.mkdir()
    setattr(cmd, "_CmdAndroidCheckAndroidQF__format", "dir")
    setattr(
        cmd,
        "_CmdAndroidCheckAndroidQF__files",
        ["androidqf/intrusion_logs/security.txt"],
    )
    monkeypatch.setattr(cmd, "_read_device_timezone", lambda: None)
    monkeypatch.setattr(
        CmdAndroidCheckIntrusionLogs,
        "run",
        record_available("intrusion_logs"),
    )

    assert cmd.run_bugreport_cmd()
    assert cmd.run_backup_cmd()
    assert cmd.run_intrusion_logs_cmd()
    assert records == {
        "bugreport": ["NestedBugreportModule"],
        "backup": ["NestedBackupModule"],
        "intrusion_logs": ["NestedIntrusionLogsModule"],
    }
