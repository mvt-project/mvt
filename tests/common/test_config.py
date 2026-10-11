# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import os

import yaml

from mvt.common import config
from mvt.common.config import MVTSettings


def test_env_variables_are_not_persisted_to_config_file(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    monkeypatch.setattr(config, "MVT_CONFIG_FOLDER", str(tmp_path))
    monkeypatch.setattr(config, "MVT_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("MVT_NETWORK_ACCESS_ALLOWED", "false")
    monkeypatch.setenv("MVT_IOS_BACKUP_PASSWORD", "env-only-password")

    settings = MVTSettings.initialise()

    assert os.path.isfile(config_path)
    saved = yaml.safe_load(config_path.read_text()) or {}
    assert "NETWORK_ACCESS_ALLOWED" not in saved
    assert "IOS_BACKUP_PASSWORD" not in saved

    # The environment must still apply to the settings in use.
    assert settings.NETWORK_ACCESS_ALLOWED is False
    assert settings.IOS_BACKUP_PASSWORD == "env-only-password"
