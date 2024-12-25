import os
import yaml
import json
import uuid

from typing import Tuple, Type, Optional
from appdirs import user_config_dir
from pydantic import AnyHttpUrl, BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    InitSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

MVT_CONFIG_FOLDER = user_config_dir("mvt")
MVT_CONFIG_PATH = os.path.join(MVT_CONFIG_FOLDER, "config.yaml")


class TelemetrySettings(BaseModel):
    """
    Settings used by the Telemetry module.
    """

    ENABLED: bool = Field(True, description="Flag for telemetry collection")
    ENDPOINT: AnyHttpUrl = Field(
        "https://t.mvt.re/events", description="Telemetry collection endpoint"
    )
    DEVICE_ID: str | None = Field(
        default=None,
        required=True,
        description="Anonymous Unique ID for use in telemetry",
    )


class MVTSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MVT_",
        env_nested_delimiter="_",
        extra="ignore",
        nested_model_default_partial_updates=True,
    )
    # Flag to enable or disable loading of environment variables.
    load_env: bool = Field(True, exclude=True)

    # General settings
    PYPI_UPDATE_URL: AnyHttpUrl = Field(
        "https://pypi.org/pypi/mvt/json",
        validate_default=False,
    )
    NETWORK_ACCESS_ALLOWED: bool = True
    NETWORK_TIMEOUT: int = 15

    # Command default settings, all can be specified by MVT_ prefixed environment variables too.
    IOS_BACKUP_PASSWORD: Optional[str] = Field(
        None, description="Default password to use to decrypt iOS backups"
    )
    ANDROID_BACKUP_PASSWORD: Optional[str] = Field(
        None, description="Default password to use to decrypt Android backups"
    )
    STIX2: Optional[str] = Field(
        None, description="List of directories where STIX2 files are stored"
    )
    VT_API_KEY: Optional[str] = Field(
        None, description="API key to use for VirusTotal lookups"
    )
    PROFILE: bool = Field(False, description="Profile the execution of MVT modules")
    HASH_FILES: bool = Field(False, description="Should MVT hash output files")

    # Telemetry settings
    TELEMETRY: TelemetrySettings = TelemetrySettings(include=True)

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
        if not settings.TELEMETRY.DEVICE_ID:
            settings.TELEMETRY.DEVICE_ID = str(uuid.uuid4())
        settings.save_settings()

        # Load the settings again with any ENV variables.
        settings = MVTSettings(load_env=True)
        return settings


settings = MVTSettings.initialise()
