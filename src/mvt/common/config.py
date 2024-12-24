import os
import uuid
import yaml
import json

from typing import Tuple, Type
from appdirs import user_config_dir
from pydantic import AnyHttpUrl, Field
from pydantic_settings import (
    BaseSettings,
    InitSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

MVT_CONFIG_FOLDER = user_config_dir("mvt")
MVT_CONFIG_PATH = os.path.join(MVT_CONFIG_FOLDER, "config.yaml")


class MVTSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MVT_", env_nested_delimiter="_", extra="ignore"
    )
    # Allow to decided if want to load environment variables
    load_env: bool = Field(True, exclude=True)

    # General settings
    PYPI_UPDATE_URL: AnyHttpUrl = Field(
        "https://pypi.org/pypi/mvt/json",
        validate_default=False,
    )
    INDICATORS_UPDATE_URL: AnyHttpUrl = Field(
        default="https://raw.githubusercontent.com/mvt-project/mvt-indicators/main/indicators.yaml",
        validate_default=False,
    )
    NETWORK_ACCESS_ALLOWED: bool = True
    NETWORK_TIMEOUT: int = 15

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: InitSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        sources = (
            YamlConfigSettingsSource(settings_cls, MVT_CONFIG_PATH),
            init_settings,
        )
        # Load env variables if enabled
        if init_settings.init_kwargs.get("load_env", True):
            sources = (env_settings,) + sources
        return sources

    def save_settings(
        self,
    ) -> None:
        """
        Save the current settings to a file.
        """
        if not os.path.isdir(MVT_CONFIG_FOLDER):
            os.makedirs(MVT_CONFIG_FOLDER)

        # Dump the settings to the YAML file
        model_serializable = json.loads(self.model_dump_json(exclude_defaults=True))
        with open(MVT_CONFIG_PATH, "w") as config_file:
            config_file.write(yaml.dump(model_serializable, default_flow_style=False))

    @classmethod
    def initialise(cls) -> "MVTSettings":
        """
        Initialise the settings file.

        We first initialise the settings (without env variable) and then persist
        them to file. This way we can update the config file with the default values.

        Afterwards we load the settings again, this time including the env variables.
        """
        # Set invalid env prefix to avoid loading env variables.
        settings = MVTSettings(load_env=False)
        settings.save_settings()

        # Load the settings again with any ENV variables.
        settings = MVTSettings(load_env=True)
        return settings


settings = MVTSettings.initialise()
