# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional, Union

from .base import IntrusionLogsModule


class DnsEvent(IntrusionLogsModule):
    """This module analyzes DNS events from intrusion logs."""

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
        """Check DNS events against indicators of compromise."""
        if not self.indicators:
            return

        for result in self.results:
            # Check hostname against domain indicators
            hostname = result.get("hostname", "")
            if hostname:
                ioc = self.indicators.check_domain(hostname)
                if ioc:
                    self.alertstore.critical(
                        ioc.message,
                        result.get("timestamp") or "",
                        result,
                        matched_indicator=ioc.ioc,
                    )

            # Check IP addresses against indicators
            ip_addresses = result.get("ip_addresses", [])
            matched_ips = []
            for ip_addr in ip_addresses:
                # Remove leading slash if present
                clean_ip = (
                    ip_addr.lstrip("/") if isinstance(ip_addr, str) else str(ip_addr)
                )
                if clean_ip and clean_ip != "0.0.0.0":
                    ioc = self.indicators.check_domain(clean_ip)
                    if ioc:
                        matched_ips.append(clean_ip)
                        self.alertstore.critical(
                            ioc.message,
                            result.get("timestamp") or "",
                            result,
                            matched_indicator=ioc.ioc,
                        )

            # Store matched IPs for timeline display
            if matched_ips:
                result["matched_ips"] = matched_ips

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
        """Serialize a DNS event record for timeline output."""
        hostname = record.get("hostname", "")
        package_name = record.get("package_name", "")

        # Get IP addresses for display
        ip_addresses = record.get("ip_addresses", [])
        matched_ips = record.get("matched_ips", [])

        # Clean up IP addresses (remove leading slashes)
        clean_ips = []
        for ip_addr in ip_addresses:
            clean_ip = ip_addr.lstrip("/") if isinstance(ip_addr, str) else str(ip_addr)
            if clean_ip and clean_ip != "0.0.0.0":
                clean_ips.append(clean_ip)

        # Build the data string with actual IPs
        if matched_ips:
            # Highlight matched IPs in the output
            ip_display = ", ".join(matched_ips)
            data = f"DNS query for {hostname} by {package_name} [Matched IPs: {ip_display}]"
        elif clean_ips:
            ip_display = ", ".join(clean_ips)
            data = f"DNS query for {hostname} by {package_name} [IPs: {ip_display}]"
        else:
            data = f"DNS query for {hostname} by {package_name}"

        return {
            "timestamp": record.get("timestamp"),
            "module": self.__class__.__name__,
            "event": "dns_query",
            "data": data,
        }

    def process_event(self, event_data: dict) -> None:
        """Process a DNS event and add it to results."""
        # Convert event_time from milliseconds to ISO format
        event_time = event_data.get("event_time")
        if event_time:
            # Android event times are in milliseconds since epoch
            event_data["timestamp"] = self._localize_timestamp(event_time / 1000.0)
        else:
            event_data["timestamp"] = None

        self.results.append(event_data)

    def run(self) -> None:
        """Extract and analyze DNS events from intrusion logs."""
        if not self.target_path:
            self.log.error("No target path specified")
            return

        self.collect_txt(self.target_path)
        self.parse_collected_txt("dns_event")

        self.log.info("Identified %d DNS events", len(self.results))
