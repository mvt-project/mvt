# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional, Union

from .base import IntrusionLogsModule


class ConnectEvent(IntrusionLogsModule):
    """This module analyzes network connection events from intrusion logs."""

    def __init__(
        self,
        file_path: Optional[str] = None,
        target_path: Optional[str] = None,
        results_path: Optional[str] = None,
        module_options: Optional[dict] = None,
        log: logging.Logger = logging.getLogger(__name__),
        results: Optional[list] = None,
    ) -> None:
        super().__init__(
            file_path=file_path,
            target_path=target_path,
            results_path=results_path,
            module_options=module_options,
            log=log,
            results=results,
        )

    def check_indicators(self) -> None:
        """Check connection events against indicators of compromise."""
        if not self.indicators:
            return

        for result in self.results:
            # Check IP address against indicators
            ip_address = result.get("ip_address", "")
            if ip_address:
                # Clean IP address (remove leading slash and extract IP from format like "ip6-localhost/::1")
                if "/" in ip_address:
                    parts = ip_address.split("/")
                    clean_ip = parts[-1] if len(parts) > 1 else parts[0]
                else:
                    clean_ip = ip_address.lstrip("/")

                # Skip localhost addresses
                if clean_ip and clean_ip not in ["::1", "127.0.0.1", "0.0.0.0"]:
                    ioc = self.indicators.check_domain(clean_ip)
                    if ioc:
                        result["matched_ip"] = clean_ip
                        self.alertstore.critical(
                            ioc.message,
                            result.get("timestamp") or "",
                            result,
                            matched_indicator=ioc.ioc,
                        )

            # Check package name against app identifiers
            package_name = result.get("package_name", "")
            if package_name:
                ioc = self.indicators.check_app_id(package_name)
                if ioc:
                    self.alertstore.critical(
                        ioc.message,
                        result.get("timestamp") or "",
                        result,
                        matched_indicator=ioc.ioc,
                    )

    def serialize(self, record: dict) -> Union[dict, list]:
        """Serialize a connection event record for timeline output."""
        ip_address = record.get("ip_address", "")
        port = record.get("port", 0)
        package_name = record.get("package_name", "")
        matched_ip = record.get("matched_ip", "")

        # Clean IP address for display
        if "/" in ip_address:
            parts = ip_address.split("/")
            clean_ip = parts[-1] if len(parts) > 1 else parts[0]
        else:
            clean_ip = ip_address.lstrip("/")

        # Indicate when IP matched an IoC
        if matched_ip:
            data = f"Connection to {clean_ip}:{port} by {package_name} [Matched IP: {matched_ip}]"
        else:
            data = f"Connection to {clean_ip}:{port} by {package_name}"

        return {
            "timestamp": record.get("timestamp"),
            "module": self.__class__.__name__,
            "event": "network_connection",
            "data": data,
        }

    def process_event(self, event_data: dict) -> None:
        """Process a connection event and add it to results."""
        # Convert event_time from milliseconds to ISO format
        event_time = event_data.get("event_time")
        if event_time:
            # Android event times are in milliseconds since epoch
            event_data["timestamp"] = self._localize_timestamp(event_time / 1000.0)
        else:
            event_data["timestamp"] = None

        self.results.append(event_data)

    def run(self) -> None:
        """Extract and analyze connection events from intrusion logs."""
        if not self.target_path:
            self.log.error("No target path specified")
            return

        self.collect_txt(self.target_path)
        self.parse_collected_txt("connect_event")

        self.log.info("Identified %d connection events", len(self.results))
