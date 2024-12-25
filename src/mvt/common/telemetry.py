# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import os
import sys
import platform
import requests
import json
import logging
import threading

from mvt.common.config import settings
from mvt.common.version import MVT_VERSION


logger = logging.getLogger(__name__)


class Telemetry(object):
    """
    MVT collects anonymous telemetry to understand how MVT is used.

    This data is helpful to prioritize features, identify platforms and versions. It
    will also how many users are using custom indicators, modules and packages.
    """

    def __init__(self):
        self.endpoint = settings.TELEMETRY.ENDPOINT
        self.device_id = settings.TELEMETRY.DEVICE_ID

    def is_telemetry_enabled(self):
        return settings.TELEMETRY.ENABLED

    @staticmethod
    def _installation_type():
        """Check if MVT is installed via pip, docker or source."""
        if "site-packages" in __file__:
            return "pypi"
        elif os.environ.get("MVT_DOCKER_IMAGE", None):
            return "docker"
        else:
            return "source"

    def _get_device_properties(self):
        return {
            "os_type": platform.system(),
            "os_version": platform.platform(),
            "python_version": f"{platform.python_version()}/{platform.python_implementation()}",
            "mvt_version": MVT_VERSION,
            "mvt_installation_type": self._installation_type(),
            "mvt_package_name": __package__,
            "mvt_command": os.path.basename(sys.argv[0]),
            "telemetry_version": "0.0.1",
        }

    def _build_event(self, event_name, event_properties):
        return {
            "event": event_name,
            "distinct_id": self.device_id,
            "properties": {
                **self._get_device_properties(),
                **event_properties,
            },
        }

    def _send_event(self, event):
        if not self.is_telemetry_enabled():
            # Telemetry is disabled. Do not send any data.
            return

        event_json = json.dumps(event)

        try:
            telemetry_thread = threading.Thread(
                target=self._send_event_thread, args=(event_json,)
            )
            telemetry_thread.start()
        except Exception as e:
            logger.debug(f"Failed to send telemetry data in a thread: {e}")

    def _send_event_thread(self, event):
        try:
            response = requests.post(
                self.endpoint,
                data=json.dumps(event),
                timeout=5,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": f"mvt/{MVT_VERSION}",
                },
            )
            response.raise_for_status()
        except requests.RequestException as e:
            logger.debug(f"Failed to send telemetry data: {e}")

    def send_cli_command_event(self, command_name):
        event = self._build_event(
            event_name="run_mvt_cli_command",
            event_properties={"cli_command_name": command_name},
        )
        self._send_event(event)

    def send_module_detections_event(self, module_name, detections):
        event = self._build_event(
            event_name="module_detections",
            event_properties={"module_name": module_name, "detections": detections},
        )
        self._send_event(event)


telemetry = Telemetry()
