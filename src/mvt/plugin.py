# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

"""Stable functions and modules which plugins can import.

Anything else in mvt can be imported too, and may change
between releases without notice.
"""

from mvt.android.modules.androidqf.base import AndroidQFModule
from mvt.android.modules.backup.base import BackupModule as AndroidBackupModule
from mvt.android.modules.bugreport.base import BugReportModule
from mvt.common.alerts import Alert, AlertLevel
from mvt.common.command import Command
from mvt.common.config import settings
from mvt.common.module import DatabaseCorruptedError, DatabaseNotFoundError, MVTModule
from mvt.common.module_loader import get_plugin_logger
from mvt.common.module_types import (
    ModuleAtomicResult,
    ModuleResults,
    ModuleSerializedResult,
)
from mvt.common.plugin_config import (
    MVTPluginSettings,
    PluginConfigLoadError,
    plugin_config_path,
    plugin_data_folder,
    plugin_env_prefix,
)
from mvt.common.utils import (
    convert_chrometime_to_datetime,
    convert_datetime_to_iso,
    convert_mactime_to_datetime,
    convert_mactime_to_iso,
    convert_unix_to_iso,
    convert_unix_to_utc_datetime,
)
from mvt.common.version import MVT_VERSION
from mvt.ios.modules.base import IOSExtraction
from mvt.ios.modules.sysdiagnose.base import SysdiagnoseExtraction

__all__ = [
    # Classes a plugin subclasses.
    "MVTModule",
    "IOSExtraction",
    "SysdiagnoseExtraction",
    "AndroidQFModule",
    "AndroidBackupModule",
    "BugReportModule",
    "Command",
    # Results and alerts.
    "ModuleAtomicResult",
    "ModuleResults",
    "ModuleSerializedResult",
    "Alert",
    "AlertLevel",
    # Errors a module raises.
    "DatabaseNotFoundError",
    "DatabaseCorruptedError",
    # Settings.
    "settings",
    "MVTPluginSettings",
    "PluginConfigLoadError",
    "plugin_config_path",
    "plugin_data_folder",
    "plugin_env_prefix",
    # Logging.
    "get_plugin_logger",
    # Timestamps.
    "convert_chrometime_to_datetime",
    "convert_datetime_to_iso",
    "convert_mactime_to_datetime",
    "convert_mactime_to_iso",
    "convert_unix_to_iso",
    "convert_unix_to_utc_datetime",
    # MVT's version.
    "MVT_VERSION",
]
