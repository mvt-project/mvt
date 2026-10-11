import hashlib
import importlib.metadata
import json

from click.testing import CliRunner

from mvt.android.cli import check_bugreport
from mvt.android.cmd_check_androidqf import CmdAndroidCheckAndroidQF
from mvt.android.cmd_check_backup import CmdAndroidCheckBackup
from mvt.android.cmd_check_bugreport import CmdAndroidCheckBugreport
from mvt.android.cmd_check_intrusion_logs import CmdAndroidCheckIntrusionLogs
from mvt.common import module_loader
from mvt.common.module import MVTModule
from mvt.common.version import MVT_VERSION
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
    (tmp_path / "Manifest.db").touch()
    (tmp_path / "Info.plist").touch()
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


class InstalledPackageModule(MVTModule):
    supported_commands = (("ios", "check-backup"),)


def get_installed_package_modules():
    return [InstalledPackageModule]


def _fake_entry_points(monkeypatch, value, name="test-modules"):
    entry_point = importlib.metadata.EntryPoint(
        name=name, value=value, group=module_loader.MODULES_ENTRY_POINT_GROUP
    )

    def fake_entry_points(*, group):
        assert group == module_loader.MODULES_ENTRY_POINT_GROUP
        return [entry_point]

    monkeypatch.setattr(
        module_loader.importlib.metadata, "entry_points", fake_entry_points
    )


def test_installed_module_package_loads_from_entry_point(monkeypatch):
    _fake_entry_points(monkeypatch, f"{__name__}:get_installed_package_modules")

    modules = module_loader.load_custom_modules()

    assert modules == [InstalledPackageModule]


def test_broken_module_entry_point_is_skipped(monkeypatch, caplog):
    _fake_entry_points(monkeypatch, "nonexistent_module_xyz:get_modules")

    with caplog.at_level("WARNING"):
        modules = module_loader.load_custom_modules()

    assert modules == []
    assert "Unable to load modules from entry point" in caplog.text


def test_entry_point_module_deduplicated_against_paths(monkeypatch, tmp_path):
    _fake_entry_points(monkeypatch, f"{__name__}:get_installed_package_modules")
    module_path = _write_custom_module(
        tmp_path / "custom.py",
        "PathLoadedModule",
        (("ios", "check-backup"),),
    )

    modules = module_loader.load_custom_modules([str(module_path)])

    assert [module.__name__ for module in modules] == [
        "InstalledPackageModule",
        "PathLoadedModule",
    ]


def test_list_modules_shows_module_sources(tmp_path, caplog):
    module_path = _write_custom_module(
        tmp_path / "custom.py",
        "SourcedBackupModule",
        (("ios", "check-backup"),),
    )
    file_sha256 = hashlib.sha256(module_path.read_bytes()).hexdigest()
    custom_modules = module_loader.load_custom_modules([str(module_path)])

    from mvt.ios.cmd_check_backup import CmdIOSCheckBackup

    cmd = CmdIOSCheckBackup(target_path=str(tmp_path), custom_modules=custom_modules)
    cmd.list_modules()

    assert f" - Modules from 'mvt@{MVT_VERSION}':" in caplog.text
    assert (
        f" - Modules from '{module_path}' (sha256: {file_sha256}): SourcedBackupModule"
        in caplog.text
    )


def test_builtin_module_origin():
    from mvt.ios.modules.backup import BACKUP_MODULES

    origin = module_loader.get_module_origin(BACKUP_MODULES[0])

    assert origin.kind == "builtin"
    assert origin.name == "mvt"
    assert origin.version == MVT_VERSION


def test_installed_module_origin(monkeypatch):
    _fake_entry_points(monkeypatch, f"{__name__}:get_installed_package_modules")

    modules = module_loader.load_custom_modules()

    origin = module_loader.get_module_origin(modules[0])
    assert origin.kind == "package"
    assert origin.name == "test-modules"


def test_distribution_commit_read_from_direct_url():
    class FakeDistribution:
        def read_text(self, filename):
            assert filename == "direct_url.json"
            return json.dumps(
                {
                    "url": "https://github.com/example/example-modules",
                    "vcs_info": {"commit_id": "abc1234", "vcs": "git"},
                }
            )

    assert module_loader._distribution_commit(FakeDistribution()) == "abc1234"


def test_command_log_records_loaded_modules(tmp_path):
    (tmp_path / "Manifest.db").touch()
    (tmp_path / "Info.plist").touch()
    module_path = _write_custom_module(
        tmp_path / "custom.py",
        "AuditedRunModule",
        (("ios", "check-backup"),),
        slug="audited_run_module",
    )
    file_sha256 = hashlib.sha256(module_path.read_bytes()).hexdigest()
    output_path = tmp_path / "out"

    result = CliRunner().invoke(
        check_backup,
        [
            "--module",
            "AuditedRunModule",
            "--load-module",
            str(module_path),
            "--output",
            str(output_path),
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    command_log = (output_path / "command.log").read_text(encoding="utf-8")
    assert (
        f"Loaded 1 check-backup modules from '{module_path}' "
        f"(sha256: {file_sha256}): AuditedRunModule" in command_log
    )


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
