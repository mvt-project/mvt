import pytest

from mvt.common.module import MVTModule
from mvt.common.module_loader import (
    CustomModuleLoadError,
    load_custom_modules,
    load_custom_modules_from_path,
    module_supports_command,
)


MODULE_TEMPLATE = """
from mvt.common.module import MVTModule


class {name}(MVTModule):
    supported_commands = {supported_commands!r}

    def run(self):
        pass

    def check_indicators(self):
        pass

    def serialize(self, result):
        return None
"""


def _write_module(path, name, supported_commands=()):
    path.write_text(
        MODULE_TEMPLATE.format(
            name=name,
            supported_commands=supported_commands,
        ),
        encoding="utf-8",
    )
    return path


def test_load_custom_modules_from_python_file(tmp_path):
    module_path = _write_module(tmp_path / "custom.py", "FileModule")

    modules = load_custom_modules_from_path(str(module_path))

    assert [module.__name__ for module in modules] == ["FileModule"]
    assert issubclass(modules[0], MVTModule)


def test_load_custom_modules_from_folder_in_sorted_order(tmp_path):
    _write_module(tmp_path / "b_module.py", "BModule")
    _write_module(tmp_path / "a_module.py", "AModule")
    _write_module(tmp_path / ".hidden.py", "HiddenModule")
    _write_module(tmp_path / "__init__.py", "InitModule")
    nested = tmp_path / "nested"
    nested.mkdir()
    _write_module(nested / "nested_module.py", "NestedModule")

    modules = load_custom_modules_from_path(str(tmp_path))

    assert [module.__name__ for module in modules] == ["AModule", "BModule"]


def test_discovery_ignores_imported_base_and_unrelated_classes(tmp_path):
    module_path = tmp_path / "custom.py"
    module_path.write_text(
        """
from mvt.common.module import MVTModule


class Unrelated:
    pass


class DiscoveredModule(MVTModule):
    def run(self):
        pass

    def check_indicators(self):
        pass

    def serialize(self, result):
        return None
""",
        encoding="utf-8",
    )

    modules = load_custom_modules_from_path(str(module_path))

    assert [module.__name__ for module in modules] == ["DiscoveredModule"]


def test_load_custom_modules_deduplicates_same_class(tmp_path):
    module_path = _write_module(tmp_path / "custom.py", "DuplicateModule")

    modules = load_custom_modules([str(module_path), str(module_path)])

    assert [module.__name__ for module in modules] == ["DuplicateModule"]


def test_load_custom_modules_raises_for_missing_path(tmp_path):
    with pytest.raises(CustomModuleLoadError, match="does not exist"):
        load_custom_modules_from_path(str(tmp_path / "missing.py"))


def test_load_custom_modules_raises_for_import_error(tmp_path):
    module_path = tmp_path / "broken.py"
    module_path.write_text("raise RuntimeError('broken import')", encoding="utf-8")

    with pytest.raises(CustomModuleLoadError, match="broken import"):
        load_custom_modules_from_path(str(module_path))


def test_load_custom_modules_loads_env_folder_first(tmp_path, monkeypatch):
    env_folder = tmp_path / "env"
    env_folder.mkdir()
    cli_folder = tmp_path / "cli"
    cli_folder.mkdir()
    _write_module(env_folder / "env_module.py", "EnvModule")
    _write_module(cli_folder / "cli_module.py", "CliModule")
    monkeypatch.setenv("MVT_CUSTOM_MODULES", str(env_folder))

    modules = load_custom_modules([str(cli_folder)])

    assert [module.__name__ for module in modules] == ["EnvModule", "CliModule"]


def test_module_supports_command_defaults_to_all_commands(tmp_path):
    module_path = _write_module(tmp_path / "custom.py", "DefaultModule")
    module = load_custom_modules_from_path(str(module_path))[0]

    assert module_supports_command(module, "ios", "check-backup")
    assert module_supports_command(module, "android", "check-bugreport")


def test_module_supports_command_honors_supported_commands(tmp_path):
    module_path = _write_module(
        tmp_path / "custom.py",
        "SpecificModule",
        (("ios", "check-backup"),),
    )
    module = load_custom_modules_from_path(str(module_path))[0]

    assert module_supports_command(module, "ios", "check-backup")
    assert not module_supports_command(module, "ios", "check-fs")
