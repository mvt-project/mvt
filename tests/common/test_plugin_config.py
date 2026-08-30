# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import os
import stat
import sys
from typing import Optional

import pytest
import yaml

from mvt.common.plugin_config import (
    MVTPluginSettings,
    PluginConfigLoadError,
    plugin_config_folder,
    plugin_config_path,
    plugin_data_folder,
    plugin_env_prefix,
)


class ExamplePluginSettings(MVTPluginSettings):
    plugin_name = "example-plugin"

    API_KEY: Optional[str] = None
    CACHE_FOLDER: str = "cache"
    MAX_RESULTS: int = 25


class OtherPluginSettings(MVTPluginSettings):
    plugin_name = "other-plugin"

    API_KEY: Optional[str] = None


@pytest.fixture
def config_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "mvt.common.plugin_config.user_config_dir",
        lambda *args, **kwargs: str(tmp_path),
    )
    return tmp_path


@pytest.fixture
def data_folder(tmp_path, monkeypatch):
    folder = tmp_path / "data"
    monkeypatch.setattr(
        "mvt.common.plugin_config.user_data_dir",
        lambda *args, **kwargs: str(folder),
    )
    return folder


def _write_plugin_file(plugin_name, values):
    config_path = plugin_config_path(plugin_name)
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    content = values if isinstance(values, str) else yaml.dump(values)
    with open(config_path, "w") as config_file:
        config_file.write(content)
    return config_path


def test_plugin_paths_and_prefixes_are_namespaced(config_folder):
    assert plugin_config_folder() == str(config_folder / "plugins")
    assert plugin_config_path("example-plugin") == str(
        config_folder / "plugins" / "example-plugin.yaml"
    )
    assert plugin_env_prefix("example-plugin") == "MVT_PLUGIN_EXAMPLE_PLUGIN_"
    assert plugin_env_prefix("other-plugin") == "MVT_PLUGIN_OTHER_PLUGIN_"


def test_defaults_are_used_without_file_or_environment(config_folder):
    settings = ExamplePluginSettings.load()

    assert settings.API_KEY is None
    assert settings.CACHE_FOLDER == "cache"
    assert settings.MAX_RESULTS == 25
    assert not os.path.exists(plugin_config_path("example-plugin"))


def test_values_are_loaded_from_the_plugin_file(config_folder):
    _write_plugin_file("example-plugin", {"API_KEY": "from-file", "MAX_RESULTS": 5})

    settings = ExamplePluginSettings.load()

    assert settings.API_KEY == "from-file"
    assert settings.MAX_RESULTS == 5
    assert settings.CACHE_FOLDER == "cache"


def test_environment_overrides_the_plugin_file(config_folder, monkeypatch):
    _write_plugin_file("example-plugin", {"API_KEY": "from-file", "MAX_RESULTS": 5})
    monkeypatch.setenv("MVT_PLUGIN_EXAMPLE_PLUGIN_API_KEY", "from-environment")

    settings = ExamplePluginSettings.load()

    assert settings.API_KEY == "from-environment"
    assert settings.MAX_RESULTS == 5


def test_arguments_override_the_environment_and_the_plugin_file(
    config_folder, monkeypatch
):
    _write_plugin_file("example-plugin", {"API_KEY": "from-file", "MAX_RESULTS": 5})
    monkeypatch.setenv("MVT_PLUGIN_EXAMPLE_PLUGIN_API_KEY", "from-environment")
    monkeypatch.setenv("MVT_PLUGIN_EXAMPLE_PLUGIN_MAX_RESULTS", "10")

    settings = ExamplePluginSettings(API_KEY="from-argument")

    assert settings.API_KEY == "from-argument"
    assert settings.MAX_RESULTS == 10


def test_save_and_load_round_trip(config_folder):
    settings = ExamplePluginSettings.load()
    settings.API_KEY = "saved-key"
    settings.MAX_RESULTS = 100

    settings.save()

    config_path = plugin_config_path("example-plugin")
    assert os.path.isfile(config_path)
    with open(config_path) as config_file:
        assert yaml.safe_load(config_file) == {
            "API_KEY": "saved-key",
            "MAX_RESULTS": 100,
        }

    reloaded = ExamplePluginSettings.load()
    assert reloaded.API_KEY == "saved-key"
    assert reloaded.MAX_RESULTS == 100
    assert reloaded.CACHE_FOLDER == "cache"


@pytest.mark.skipif(
    sys.platform == "win32", reason="POSIX file permissions are not available"
)
def test_saved_file_is_only_readable_by_the_user(config_folder):
    settings = ExamplePluginSettings.load()
    settings.API_KEY = "saved-key"

    settings.save()

    config_path = plugin_config_path("example-plugin")
    assert stat.S_IMODE(os.stat(config_path).st_mode) == 0o600
    folder_mode = stat.S_IMODE(os.stat(plugin_config_folder()).st_mode)
    assert folder_mode & 0o077 == 0


@pytest.mark.skipif(
    sys.platform == "win32", reason="POSIX file permissions are not available"
)
def test_save_restricts_the_permissions_of_an_existing_file(config_folder):
    config_path = _write_plugin_file("example-plugin", {"API_KEY": "from-file"})
    os.chmod(config_path, 0o644)

    settings = ExamplePluginSettings.load()
    settings.MAX_RESULTS = 100
    settings.save()

    assert stat.S_IMODE(os.stat(config_path).st_mode) == 0o600
    assert os.listdir(plugin_config_folder()) == ["example-plugin.yaml"]


def test_save_only_persists_non_default_values(config_folder):
    settings = ExamplePluginSettings.load()
    settings.CACHE_FOLDER = "another-cache"

    settings.save()

    with open(plugin_config_path("example-plugin")) as config_file:
        assert yaml.safe_load(config_file) == {"CACHE_FOLDER": "another-cache"}


def test_save_does_not_persist_values_coming_from_the_environment(
    config_folder, monkeypatch
):
    monkeypatch.setenv("MVT_PLUGIN_EXAMPLE_PLUGIN_API_KEY", "environment-secret")

    settings = ExamplePluginSettings.load()
    assert settings.API_KEY == "environment-secret"
    settings.MAX_RESULTS = 100
    settings.save()

    with open(plugin_config_path("example-plugin")) as config_file:
        assert yaml.safe_load(config_file) == {"MAX_RESULTS": 100}


def test_an_invalid_environment_variable_still_protects_the_other_values(
    config_folder, monkeypatch
):
    monkeypatch.setenv("MVT_PLUGIN_EXAMPLE_PLUGIN_API_KEY", "environment-secret")
    monkeypatch.setenv("MVT_PLUGIN_EXAMPLE_PLUGIN_MAX_RESULTS", "not-an-int")

    settings = ExamplePluginSettings(MAX_RESULTS=100)
    assert settings.API_KEY == "environment-secret"
    settings.save()

    with open(plugin_config_path("example-plugin")) as config_file:
        saved_values = yaml.safe_load(config_file)
    assert saved_values == {"MAX_RESULTS": 100}
    assert "API_KEY" not in saved_values


def test_save_persists_values_which_differ_from_the_environment(
    config_folder, monkeypatch
):
    monkeypatch.setenv("MVT_PLUGIN_EXAMPLE_PLUGIN_API_KEY", "environment-secret")

    settings = ExamplePluginSettings.load()
    settings.API_KEY = "chosen-key"
    settings.save()

    with open(plugin_config_path("example-plugin")) as config_file:
        assert yaml.safe_load(config_file) == {"API_KEY": "chosen-key"}


def test_save_does_not_write_the_mvt_configuration_file(config_folder):
    settings = ExamplePluginSettings.load()
    settings.API_KEY = "saved-key"

    settings.save()

    assert os.listdir(config_folder) == ["plugins"]


def test_unknown_keys_in_the_plugin_file_are_ignored(config_folder):
    _write_plugin_file(
        "example-plugin",
        {"API_KEY": "from-file", "UNKNOWN_SETTING": "ignored"},
    )

    settings = ExamplePluginSettings.load()

    assert settings.API_KEY == "from-file"
    assert not hasattr(settings, "UNKNOWN_SETTING")


def test_unparsable_plugin_file_is_reported_with_its_path(config_folder):
    config_path = _write_plugin_file("example-plugin", "API_KEY: [unclosed\n")

    with pytest.raises(PluginConfigLoadError) as raised:
        ExamplePluginSettings.load()

    assert config_path in str(raised.value)


def test_plugin_file_which_is_not_a_mapping_is_reported_with_its_path(config_folder):
    config_path = _write_plugin_file("example-plugin", "- one\n- two\n")

    with pytest.raises(PluginConfigLoadError) as raised:
        ExamplePluginSettings.load()

    assert config_path in str(raised.value)
    assert "mapping of setting names" in str(raised.value)


def test_plugins_do_not_interfere_with_each_other(config_folder, monkeypatch):
    _write_plugin_file("other-plugin", {"API_KEY": "other-file-key"})
    monkeypatch.setenv("MVT_PLUGIN_EXAMPLE_PLUGIN_API_KEY", "example-environment-key")

    example_settings = ExamplePluginSettings.load()
    other_settings = OtherPluginSettings.load()

    assert example_settings.API_KEY == "example-environment-key"
    assert other_settings.API_KEY == "other-file-key"

    example_settings.MAX_RESULTS = 100
    example_settings.save()
    assert sorted(os.listdir(plugin_config_folder())) == [
        "example-plugin.yaml",
        "other-plugin.yaml",
    ]
    with open(plugin_config_path("other-plugin")) as config_file:
        assert yaml.safe_load(config_file) == {"API_KEY": "other-file-key"}


def test_subclass_without_plugin_name_is_rejected():
    with pytest.raises(TypeError, match="plugin_name"):

        class MissingNameSettings(MVTPluginSettings):
            API_KEY: Optional[str] = None


def test_subclass_with_invalid_plugin_name_is_rejected():
    with pytest.raises(ValueError, match="Invalid plugin name"):

        class InvalidNameSettings(MVTPluginSettings):
            plugin_name = "Bad/Name"


def test_underscores_are_not_allowed_in_plugin_names():
    # Underscores are replaced by dashes in the environment prefix, so allowing
    # both would let two plugin names share one environment namespace.
    with pytest.raises(ValueError, match="Invalid plugin name"):

        class UnderscoreNameSettings(MVTPluginSettings):
            plugin_name = "under_score"

    with pytest.raises(ValueError, match="Invalid plugin name"):
        plugin_config_path("under_score")
    with pytest.raises(ValueError, match="Invalid plugin name"):
        plugin_env_prefix("under_score")


@pytest.mark.parametrize(
    "plugin_name", ["../escape", "folder/name", "UPPER", "-dash", ""]
)
def test_unsafe_plugin_names_have_no_configuration_path(plugin_name):
    with pytest.raises(ValueError, match="Invalid plugin name"):
        plugin_config_path(plugin_name)


def test_data_folder_is_namespaced_and_created(data_folder):
    folder = plugin_data_folder("example-plugin")

    assert folder == str(data_folder / "plugin-data" / "example-plugin")
    assert os.path.isdir(folder)


def test_data_folder_can_be_requested_repeatedly(data_folder):
    folder = plugin_data_folder("example-plugin")
    with open(os.path.join(folder, "kept.json"), "w") as data_file:
        data_file.write("{}")

    assert plugin_data_folder("example-plugin") == folder
    assert os.listdir(folder) == ["kept.json"]


@pytest.mark.skipif(
    sys.platform == "win32", reason="POSIX file permissions are not available"
)
def test_data_folder_is_only_accessible_by_the_user(data_folder):
    folder = plugin_data_folder("example-plugin")

    assert stat.S_IMODE(os.stat(folder).st_mode) & 0o077 == 0
    parent_mode = stat.S_IMODE(os.stat(os.path.dirname(folder)).st_mode)
    assert parent_mode & 0o077 == 0


def test_plugins_get_their_own_data_folder(data_folder):
    example_folder = plugin_data_folder("example-plugin")
    other_folder = plugin_data_folder("other-plugin")

    assert example_folder != other_folder
    assert sorted(os.listdir(data_folder / "plugin-data")) == [
        "example-plugin",
        "other-plugin",
    ]


def test_data_folder_does_not_touch_the_configuration_folder(
    config_folder, data_folder
):
    plugin_data_folder("example-plugin")

    assert not os.path.exists(plugin_config_folder())


@pytest.mark.parametrize(
    "plugin_name", ["../escape", "folder/name", "UPPER", "-dash", ""]
)
def test_unsafe_plugin_names_have_no_data_folder(data_folder, plugin_name):
    with pytest.raises(ValueError, match="Invalid plugin name"):
        plugin_data_folder(plugin_name)

    assert not os.path.exists(data_folder)


def test_settings_class_knows_its_data_folder(data_folder):
    folder = ExamplePluginSettings.data_folder()

    assert folder == plugin_data_folder("example-plugin")
    assert os.path.isdir(folder)
    assert OtherPluginSettings.data_folder() != folder


def test_settings_instance_uses_the_same_data_folder(config_folder, data_folder):
    settings = ExamplePluginSettings.load()

    assert settings.data_folder() == ExamplePluginSettings.data_folder()


def test_subclass_without_its_own_name_shares_the_data_folder(data_folder):
    class InheritingSettings(ExamplePluginSettings):
        pass

    assert InheritingSettings.data_folder() == ExamplePluginSettings.data_folder()
