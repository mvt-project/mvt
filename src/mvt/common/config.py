import json
import os
from typing import Optional, Tuple, Type

import yaml
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
        env_prefix="MVT_",
        env_nested_delimiter="_",
        extra="ignore",
    )
    # Allow to decided if want to load environment variables
    load_env: bool = Field(True, exclude=True)

    # General settings
    PYPI_UPDATE_URL: str = Field(
        default="https://pypi.org/pypi/mvt/json",
    )
    NETWORK_ACCESS_ALLOWED: bool = True
    NETWORK_TIMEOUT: int = 15

    # Command default settings, all can be specified by MVT_ prefixed environment variables too.
    IOS_BACKUP_PASSWORD: Optional[str] = Field(
        default=None, description="Default password to use to decrypt iOS backups"
    )
    ANDROID_BACKUP_PASSWORD: Optional[str] = Field(
        default=None, description="Default password to use to decrypt Android backups"
    )
    STIX2: Optional[str] = Field(
        default=None, description="List of directories where STIX2 files are stored"
    )
    VT_API_KEY: Optional[str] = Field(
        default=None, description="API key to use for VirusTotal lookups"
    )
    PROFILE: bool = Field(
        default=False, description="Profile the execution of MVT modules"
    )
    HASH_FILES: bool = Field(default=False, description="Should MVT hash output files")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        yaml_source = YamlConfigSettingsSource(settings_cls, MVT_CONFIG_PATH)
        sources: Tuple[PydanticBaseSettingsSource, ...] = (
            yaml_source,
            init_settings,
        )
        # Always load env variables by default
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
        settings = cls(load_env=False)
        settings.save_settings()

        # Load the settings again with any ENV variables.
        settings = cls(load_env=True)
        return settings


settings = MVTSettings.initialise()
