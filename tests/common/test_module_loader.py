import pytest

from mvt.common.module import MVTModule
from mvt.common.module_loader import (
    CustomModuleLoadError,
    get_module_logger,
    load_custom_modules,
    load_custom_modules_from_path,
    module_supports_command,
)
from mvt.ios.modules.mixed.whatsapp import Whatsapp


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


def test_module_supports_command_requires_explicit_declaration(tmp_path, caplog):
    module_path = _write_module(tmp_path / "custom.py", "DefaultModule")
    module = load_custom_modules_from_path(str(module_path))[0]

    assert not module_supports_command(module, "ios", "check-backup")
    assert not module_supports_command(module, "android", "check-bugreport")
    assert "DefaultModule has no supported_commands" in caplog.text


def test_module_supports_command_honors_supported_commands(tmp_path):
    module_path = _write_module(
        tmp_path / "custom.py",
        "SpecificModule",
        (("ios", "check-backup"),),
    )
    module = load_custom_modules_from_path(str(module_path))[0]

    assert module_supports_command(module, "ios", "check-backup")
    assert not module_supports_command(module, "ios", "check-fs")


def test_get_module_logger_keeps_builtin_names():
    assert get_module_logger(Whatsapp).name == "mvt.ios.modules.mixed.whatsapp"


def test_get_module_logger_parents_package_modules_under_mvt_ext():
    class PackageModule(MVTModule):
        pass

    PackageModule.__module__ = "some_plugin_package.ios.custom"

    assert (
        get_module_logger(PackageModule).name
        == "mvt.ext.some_plugin_package.ios.custom"
    )


def test_get_module_logger_strips_the_plugin_package_prefix():
    class PluginModule(MVTModule):
        pass

    PluginModule.__module__ = "mvt_plugin_amnesty_custom.ios.custom"

    assert get_module_logger(PluginModule).name == "mvt.ext.amnesty_custom.ios.custom"


def test_get_module_logger_only_strips_the_prefix_from_the_top_level():
    class NestedModule(MVTModule):
        pass

    NestedModule.__module__ = "other_package.mvt_plugin_sub"

    assert get_module_logger(NestedModule).name == "mvt.ext.other_package.mvt_plugin_sub"


def test_get_module_logger_names_path_modules_after_their_file(tmp_path):
    module_path = _write_module(tmp_path / "my_custom_module.py", "PathModule")
    module = load_custom_modules_from_path(str(module_path))[0]

    assert get_module_logger(module).name == "mvt.ext.my_custom_module"
