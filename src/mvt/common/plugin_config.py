# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import contextlib
import json
import os
import re
import tempfile
from typing import Any, ClassVar, Dict, List, Tuple, Type, TypeVar

import yaml
from appdirs import user_config_dir, user_data_dir
from pydantic import ValidationError
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

PLUGIN_CONFIG_FOLDER_NAME = "plugins"
# Not "plugins": on macOS the configuration and data folders are the same
# directory, and that name already holds the settings files.
PLUGIN_DATA_FOLDER_NAME = "plugin-data"
PLUGIN_ENV_PREFIX = "MVT_PLUGIN_"

PLUGIN_NAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*")

PluginSettingsType = TypeVar("PluginSettingsType", bound="MVTPluginSettings")


class PluginConfigLoadError(Exception):
    pass


def validate_plugin_name(plugin_name: Any) -> str:
    """
    Check that a plugin name is safe to use in a file name and an env variable.

    :param plugin_name: Name to validate.
    :returns: The validated plugin name.
    """
    if not isinstance(plugin_name, str):
        raise TypeError(
            f"Plugin name must be a string, not {type(plugin_name).__name__}"
        )
    if not PLUGIN_NAME_PATTERN.fullmatch(plugin_name):
        raise ValueError(
            f"Invalid plugin name {plugin_name!r}: plugin names must start with a "
            "lowercase letter or a digit and may only contain lowercase letters, "
            "digits and dashes"
        )
    return plugin_name


def plugin_config_folder() -> str:
    """
    Return the folder where plugins store their configuration files.

    The path is resolved on every call so it always reflects the current
    environment.
    """
    return os.path.join(user_config_dir("mvt"), PLUGIN_CONFIG_FOLDER_NAME)


def plugin_config_path(plugin_name: str) -> str:
    """
    Return the path of the configuration file of a given plugin.

    :param plugin_name: Name of the plugin.
    """
    return os.path.join(
        plugin_config_folder(), f"{validate_plugin_name(plugin_name)}.yaml"
    )


def plugin_data_folder(plugin_name: str) -> str:
    """
    Return the folder where a given plugin stores its data, creating it.

    Plugins should keep whatever they persist, such as caches or downloaded
    artifacts, in this folder. It is created with owner-only permissions. The
    path is resolved on every call so it always reflects the current
    environment. A plugin with a settings class calls
    `MVTPluginSettings.data_folder()` instead, which passes `plugin_name` here.

    :param plugin_name: Name of the plugin.
    :returns: The path of the data folder of the plugin.
    """
    # Validate the name before anything is created, so an unsafe name cannot
    # leave a folder behind.
    name = validate_plugin_name(plugin_name)

    # makedirs() applies its mode only to the last folder of the path, so
    # MVT's own data folder keeps the default permissions while the two
    # plugin folders are private.
    data_folder = os.path.join(user_data_dir("mvt"), PLUGIN_DATA_FOLDER_NAME)
    os.makedirs(data_folder, mode=0o700, exist_ok=True)

    folder = os.path.join(data_folder, name)
    os.makedirs(folder, mode=0o700, exist_ok=True)
    return folder


def plugin_env_prefix(plugin_name: str) -> str:
    """
    Return the environment variable prefix used by a given plugin.

    Dashes are replaced by underscores. Plugin names cannot contain underscores,
    so two different plugin names never share an environment namespace.

    :param plugin_name: Name of the plugin.
    """
    name = validate_plugin_name(plugin_name).upper().replace("-", "_")
    return f"{PLUGIN_ENV_PREFIX}{name}_"


def _settings_plugin_name(settings_cls: Type[BaseSettings]) -> str:
    plugin_name = getattr(settings_cls, "plugin_name", None)
    if plugin_name is None:
        raise TypeError(
            f"{settings_cls.__name__} must set a 'plugin_name' class attribute to "
            "namespace its configuration file and environment variables"
        )
    return validate_plugin_name(plugin_name)


def _plugin_yaml_source(
    settings_cls: Type[BaseSettings], config_path: str
) -> YamlConfigSettingsSource:
    """
    Build the YAML settings source of a plugin, reporting unusable files.

    A missing file is not an error, but a file which cannot be parsed or which
    does not hold a mapping of setting names is reported with its path.
    """
    try:
        return YamlConfigSettingsSource(settings_cls, config_path)
    except yaml.YAMLError as exc:
        raise PluginConfigLoadError(
            f"Invalid plugin configuration file {config_path}: {exc}"
        ) from exc
    except (TypeError, ValueError) as exc:
        raise PluginConfigLoadError(
            f"Invalid plugin configuration file {config_path}: the file must "
            "contain a mapping of setting names to values"
        ) from exc


class MVTPluginSettings(BaseSettings):
    """
    Base class for plugin-namespaced settings.

    Subclass with typed fields and set `plugin_name`. Values resolve from
    constructor arguments, then environment variables (MVT_PLUGIN_<NAME>_*),
    then the plugin's YAML file (~/.config/mvt/plugins/<name>.yaml), then field
    defaults.

    Plugins must not store their settings in MVT's own configuration file: MVT
    rewrites it with the fields it knows about, dropping anything else.

    `data_folder()` returns the folder the plugin keeps its data in.
    """

    model_config = SettingsConfigDict(extra="ignore")

    plugin_name: ClassVar[str]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        plugin_name = _settings_plugin_name(cls)
        # Namespace the environment variables of this plugin. Each pydantic
        # model gets its own configuration dictionary, so this does not leak
        # into other plugins.
        cls.model_config["env_prefix"] = plugin_env_prefix(plugin_name)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        config_path = plugin_config_path(_settings_plugin_name(settings_cls))
        yaml_source = _plugin_yaml_source(settings_cls, config_path)
        # Explicit arguments take precedence over environment variables, which
        # in turn take precedence over the configuration file.
        return (init_settings, env_settings, yaml_source)

    @classmethod
    def load(cls: Type[PluginSettingsType]) -> PluginSettingsType:
        """
        Load the settings of the plugin.

        A missing configuration file is not an error: the settings then come
        from the environment and from the field defaults.
        """
        return cls()

    @classmethod
    def data_folder(cls) -> str:
        """
        Return the data folder of the plugin, creating it.

        The folder is the one plugin_data_folder() returns for `plugin_name`,
        so a plugin with a settings class does not repeat its name.
        """
        return plugin_data_folder(_settings_plugin_name(cls))

    def _environment_values(self) -> Dict[str, Any]:
        """
        Return the settings values currently supplied by the environment.

        Values are validated by the model, so they can be compared with the
        values held by this instance.
        """
        settings_cls = type(self)
        raw_values = EnvSettingsSource(settings_cls)()
        names = [name for name in raw_values if name in settings_cls.model_fields]
        if not names:
            return {}

        # Fall back on the current values for the fields the environment does
        # not set, so that required fields do not fail validation here.
        current_values = json.loads(self.model_dump_json())
        try:
            from_environment = settings_cls.model_validate(
                {**current_values, **raw_values}
            )
        except ValidationError:
            # An environment variable which the model cannot validate must not
            # stop the other environment values from being recognised, or a
            # credential would be written to the configuration file.
            return self._environment_values_by_field(current_values, raw_values, names)
        return {name: getattr(from_environment, name) for name in names}

    def _environment_values_by_field(
        self,
        current_values: Dict[str, Any],
        raw_values: Dict[str, Any],
        names: List[str],
    ) -> Dict[str, Any]:
        """
        Validate each environment value on its own, skipping unusable ones.

        :param current_values: Serialized values held by this instance.
        :param raw_values: Values supplied by the environment.
        :param names: Names of the fields set by the environment.
        """
        settings_cls = type(self)
        values = {}
        for name in names:
            try:
                from_environment = settings_cls.model_validate(
                    {**current_values, name: raw_values[name]}
                )
            except ValidationError:
                continue
            values[name] = getattr(from_environment, name)
        return values

    def save(self) -> None:
        """
        Save the current settings to the configuration file of the plugin.

        Only values which differ from the field defaults are persisted. Values
        which come from the environment are not written to disk, so credentials
        passed as environment variables stay out of the configuration file.
        MVT's own configuration file is never modified.
        """
        config_folder = plugin_config_folder()
        if not os.path.isdir(config_folder):
            os.makedirs(config_folder, mode=0o700, exist_ok=True)

        values = json.loads(self.model_dump_json(exclude_defaults=True))
        for name, environment_value in self._environment_values().items():
            if name in values and getattr(self, name, None) == environment_value:
                del values[name]

        # Settings files can hold credentials, so write them through a private
        # temporary file and move it in place. The file is then never partially
        # written and never briefly readable by other users.
        config_path = plugin_config_path(self.plugin_name)
        descriptor, temporary_path = tempfile.mkstemp(
            dir=config_folder, prefix=f".{self.plugin_name}-", suffix=".yaml"
        )
        try:
            with os.fdopen(descriptor, "w") as config_file:
                config_file.write(yaml.dump(values, default_flow_style=False))
            os.replace(temporary_path, config_path)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(temporary_path)
            raise
