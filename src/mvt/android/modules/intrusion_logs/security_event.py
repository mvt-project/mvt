# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import logging
from typing import Optional, Union

from .base import IntrusionLogsModule

# Security event tags based on Android SecurityLog API
# Reference: https://developer.android.com/reference/android/app/admin/SecurityLog
SECURITY_EVENT_TAGS = {
    # ADB events (API level 24)
    "adb_shell_interactive": {
        "tag_id": 210001,
        "name": "ADB Shell Interactive",
        "description": "An ADB interactive shell was opened via 'adb shell'",
    },
    "adb_shell_cmd": {
        "tag_id": 210002,
        "name": "ADB Shell Command",
        "description": "A shell command was issued over ADB via 'adb shell <command>'",
    },
    "adb_sync_recv_file": {
        "tag_id": 210003,
        "name": "ADB Sync Recv File",
        "description": "A file was pulled from the device via adb daemon (adb pull)",
    },
    "adb_sync_send_file": {
        "tag_id": 210004,
        "name": "ADB Sync Send File",
        "description": "A file was pushed to the device via adb daemon (adb push)",
    },
    # App process events (API level 24)
    "app_process_start": {
        "tag_id": 210005,
        "name": "App Process Start",
        "description": "An app process was started",
    },
    # Keyguard events (API level 24)
    "keyguard_dismissed": {
        "tag_id": 210006,
        "name": "Keyguard Dismissed",
        "description": "Keyguard has been dismissed",
    },
    "keyguard_dismiss_auth_attempt": {
        "tag_id": 210007,
        "name": "Keyguard Dismiss Auth Attempt",
        "description": "Authentication attempt to dismiss keyguard",
    },
    "keyguard_secured": {
        "tag_id": 210008,
        "name": "Keyguard Secured",
        "description": "Device has been locked",
    },
    # OS events (API level 28)
    "os_startup": {
        "tag_id": 210009,
        "name": "OS Startup",
        "description": "Android OS has started",
    },
    "os_shutdown": {
        "tag_id": 210010,
        "name": "OS Shutdown",
        "description": "Android OS has shutdown",
    },
    # Logging events (API level 28)
    "logging_started": {
        "tag_id": 210011,
        "name": "Logging Started",
        "description": "Audit logging has started",
    },
    "logging_stopped": {
        "tag_id": 210012,
        "name": "Logging Stopped",
        "description": "Audit logging has stopped",
    },
    # Media events (API level 28)
    "media_mount": {
        "tag_id": 210013,
        "name": "Media Mount",
        "description": "Removable media has been mounted",
    },
    "media_unmount": {
        "tag_id": 210014,
        "name": "Media Unmount",
        "description": "Removable media was unmounted",
    },
    # Log buffer event (API level 28)
    "log_buffer_size_critical": {
        "tag_id": 210015,
        "name": "Log Buffer Size Critical",
        "description": "Audit log buffer has reached 90% capacity",
    },
    # Password policy events (API level 28)
    "password_expiration_set": {
        "tag_id": 210016,
        "name": "Password Expiration Set",
        "description": "Admin set password expiration timeout",
    },
    "password_complexity_set": {
        "tag_id": 210017,
        "name": "Password Complexity Set",
        "description": "Admin set password complexity requirement",
    },
    "password_history_length_set": {
        "tag_id": 210018,
        "name": "Password History Length Set",
        "description": "Admin set password history length",
    },
    "max_screen_lock_timeout_set": {
        "tag_id": 210019,
        "name": "Max Screen Lock Timeout Set",
        "description": "Admin set maximum screen lock timeout",
    },
    "max_password_attempts_set": {
        "tag_id": 210020,
        "name": "Max Password Attempts Set",
        "description": "Admin set maximum failed password attempts before wipe",
    },
    "keyguard_disabled_features_set": {
        "tag_id": 210021,
        "name": "Keyguard Disabled Features Set",
        "description": "Admin set disabled keyguard features",
    },
    # Remote lock event (API level 28)
    "remote_lock": {
        "tag_id": 210022,
        "name": "Remote Lock",
        "description": "Admin remotely locked the device or profile",
    },
    # Wipe failure event (API level 28)
    "wipe_failure": {
        "tag_id": 210023,
        "name": "Wipe Failure",
        "description": "Failed to wipe device or user data",
    },
    # Cryptographic key events (API level 28)
    "key_generated": {
        "tag_id": 210024,
        "name": "Key Generated",
        "description": "Cryptographic key was generated",
    },
    "key_import": {
        "tag_id": 210025,
        "name": "Key Import",
        "description": "Cryptographic key was imported",
    },
    "key_destruction": {
        "tag_id": 210026,
        "name": "Key Destruction",
        "description": "Cryptographic key was destroyed",
    },
    # User restriction events (API level 28)
    "user_restriction_added": {
        "tag_id": 210027,
        "name": "User Restriction Added",
        "description": "Admin added a user restriction",
    },
    "user_restriction_removed": {
        "tag_id": 210028,
        "name": "User Restriction Removed",
        "description": "Admin removed a user restriction",
    },
    # Certificate events (API level 28)
    "cert_authority_installed": {
        "tag_id": 210029,
        "name": "Certificate Authority Installed",
        "description": "Root certificate installed to trusted storage",
    },
    "cert_authority_removed": {
        "tag_id": 210030,
        "name": "Certificate Authority Removed",
        "description": "Root certificate removed from trusted storage",
    },
    "crypto_self_test_completed": {
        "tag_id": 210031,
        "name": "Crypto Self Test Completed",
        "description": "Cryptographic functionality self test completed",
    },
    "key_integrity_violation": {
        "tag_id": 210032,
        "name": "Key Integrity Violation",
        "description": "Key integrity violation detected",
    },
    "cert_validation_failure": {
        "tag_id": 210033,
        "name": "Certificate Validation Failure",
        "description": "X.509v3 certificate validation failed",
    },
    # Camera policy event (API level 30)
    "camera_policy_set": {
        "tag_id": 210034,
        "name": "Camera Policy Set",
        "description": "Admin set policy to disable camera",
    },
    # Password complexity events (API level 31/33)
    "password_complexity_required": {
        "tag_id": 210035,
        "name": "Password Complexity Required",
        "description": "Admin set password complexity requirement using predefined levels",
    },
    "password_changed": {
        "tag_id": 210036,
        "name": "Password Changed",
        "description": "User changed their lockscreen password",
    },
    # WiFi events (API level 33)
    "wifi_connection": {
        "tag_id": 210037,
        "name": "WiFi Connection",
        "description": "Device attempted to connect to a managed WiFi network",
    },
    "wifi_disconnection": {
        "tag_id": 210038,
        "name": "WiFi Disconnection",
        "description": "Device disconnected from a managed WiFi network",
    },
    # Bluetooth events (API level 33)
    "bluetooth_connection": {
        "tag_id": 210039,
        "name": "Bluetooth Connection",
        "description": "Device attempted to connect to a Bluetooth device",
    },
    "bluetooth_disconnection": {
        "tag_id": 210040,
        "name": "Bluetooth Disconnection",
        "description": "Device disconnected from a Bluetooth device",
    },
    # Package events (API level 34)
    "package_installed": {
        "tag_id": 210041,
        "name": "Package Installed",
        "description": "Application package was installed",
    },
    "package_updated": {
        "tag_id": 210042,
        "name": "Package Updated",
        "description": "Application package was updated",
    },
    "package_uninstalled": {
        "tag_id": 210043,
        "name": "Package Uninstalled",
        "description": "Application package was uninstalled",
    },
    # Backup service event (API level 35)
    "backup_service_toggled": {
        "tag_id": 210044,
        "name": "Backup Service Toggled",
        "description": "Admin enabled or disabled backup service",
    },
    # NFC events (API level 36)
    "nfc_enabled": {
        "tag_id": 210045,
        "name": "NFC Enabled",
        "description": "NFC service is enabled",
    },
    "nfc_disabled": {
        "tag_id": 210046,
        "name": "NFC Disabled",
        "description": "NFC service is disabled",
    },
}

SECURITY_EVENT_METADATA_KEYS = {
    "event_time",
    "event_type",
    "timestamp",
}


class SecurityEvent(IntrusionLogsModule):
    """This module analyzes security events from intrusion logs."""

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
        self.event_type_counts: dict[str, int] = {}

    def _get_event_tag(self, event_data: dict) -> Optional[str]:
        """Return the security-event tag key, including tags unknown to MVT."""
        for key in event_data:
            if key not in SECURITY_EVENT_METADATA_KEYS:
                return key

        return None

    def check_indicators(self) -> None:
        """Check security events against indicators of compromise."""
        if not self.indicators:
            return

        for result in self.results:
            # Check app process start events for suspicious package names
            if "app_process_start" in result:
                process_info = result["app_process_start"]
                process_name = process_info.get("process", "")
                if process_name:
                    # Check the full process name
                    ioc = self.indicators.check_app_id(process_name)
                    if ioc:
                        self.alertstore.critical(
                            ioc.message,
                            result.get("timestamp") or "",
                            result,
                            matched_indicator=ioc.ioc,
                        )

                    # Also check process components after the first colon
                    # Example: "com.google.android.webview:sandboxed_process0:org.chromium.content.app.SandboxedProcessService0:0"
                    # We want to check "sandboxed_process0" and subsequent components
                    if ":" in process_name:
                        components = process_name.split(":")
                        for component in components[
                            1:
                        ]:  # Skip the first component (main package name)
                            if component:
                                ioc = self.indicators.check_app_id(component)
                                if ioc:
                                    self.alertstore.critical(
                                        ioc.message,
                                        result.get("timestamp") or "",
                                        result,
                                        matched_indicator=ioc.ioc,
                                    )
                                    break

            # Check package operations for suspicious packages
            for pkg_event in [
                "package_installed",
                "package_updated",
                "package_uninstalled",
            ]:
                if pkg_event in result:
                    pkg_info = result[pkg_event]
                    pkg_name = pkg_info.get("package_name", "")
                    if pkg_name:
                        ioc = self.indicators.check_app_id(pkg_name)
                        if ioc:
                            self.alertstore.critical(
                                ioc.message,
                                result.get("timestamp") or "",
                                result,
                                matched_indicator=ioc.ioc,
                            )

            # Check ADB shell commands for suspicious patterns
            if "adb_shell_cmd" in result:
                cmd_info = result["adb_shell_cmd"]
                command = cmd_info.get("command", "")
                if command:
                    # Check if command contains any suspicious app IDs
                    ioc = self.indicators.check_app_id(command)
                    if ioc:
                        self.alertstore.critical(
                            ioc.message,
                            result.get("timestamp") or "",
                            result,
                            matched_indicator=ioc.ioc,
                        )

            # Check ADB file sync events for suspicious paths
            for adb_event in ["adb_sync_recv_file", "adb_sync_send_file"]:
                if adb_event in result:
                    file_info = result[adb_event]
                    file_path = file_info.get("path", "")
                    if file_path:
                        ioc = self.indicators.check_file_path(file_path)
                        if ioc:
                            self.alertstore.critical(
                                ioc.message,
                                result.get("timestamp") or "",
                                result,
                                matched_indicator=ioc.ioc,
                            )

            # Flag failed cryptographic operations as potentially suspicious
            if "key_generated" in result:
                if not result["key_generated"].get("success", True):
                    self.log.warning(
                        "Failed key generation detected for key_id: %s",
                        result["key_generated"].get("key_id", "unknown"),
                    )

            # Flag certificate validation failures
            if "cert_validation_failure" in result:
                self.log.warning(
                    "Certificate validation failure detected: %s",
                    result.get("cert_validation_failure"),
                )

            # Flag key integrity violations
            if "key_integrity_violation" in result:
                self.alertstore.medium(
                    f"Key integrity violation detected: {result.get('key_integrity_violation')}",
                    result.get("timestamp") or "",
                    result,
                )

            # Flag certificate authority installations (potential MITM)
            if "cert_authority_installed" in result:
                cert_info = result["cert_authority_installed"]
                self.log.warning(
                    "Certificate authority installed: %s (success: %s)",
                    cert_info.get("subject", "unknown"),
                    cert_info.get("success", "unknown"),
                )

            # Flag wipe failures
            if "wipe_failure" in result:
                self.alertstore.medium(
                    "Device wipe failure detected",
                    result.get("timestamp") or "",
                    result,
                )

            # Flag crypto self test failures
            if "crypto_self_test_completed" in result:
                test_result = result["crypto_self_test_completed"]
                if isinstance(test_result, dict):
                    success = test_result.get("success", True)
                else:
                    success = test_result == 1
                if not success:
                    self.alertstore.medium(
                        "Cryptographic self test failed",
                        result.get("timestamp") or "",
                        result,
                    )

    def serialize(self, record: dict) -> Union[dict, list]:
        """Serialize a security event record for timeline output."""
        # Determine the event sub-type
        event_subtype = None
        event_data_str = ""

        event_subtype = self._get_event_tag(record)
        if event_subtype:
            event_info = record[event_subtype]

            if event_subtype in SECURITY_EVENT_TAGS:
                # ADB events
                if event_subtype == "adb_shell_interactive":
                    event_data_str = "ADB interactive shell opened"
                elif event_subtype == "adb_shell_cmd":
                    command = event_info.get("command", "")
                    event_data_str = f"ADB shell command: {command}"
                elif event_subtype == "adb_sync_recv_file":
                    path = event_info.get("path", "")
                    event_data_str = f"File pulled via ADB: {path}"
                elif event_subtype == "adb_sync_send_file":
                    path = event_info.get("path", "")
                    event_data_str = f"File pushed via ADB: {path}"

                # App process events
                elif event_subtype == "app_process_start":
                    process_name = event_info.get("process", "")
                    uid = event_info.get("uid", "")
                    pid = event_info.get("pid", "")
                    event_data_str = (
                        f"Process started: {process_name} (UID: {uid}, PID: {pid})"
                    )

                # Keyguard events
                elif event_subtype == "keyguard_dismiss_auth_attempt":
                    success = event_info.get("success", False)
                    method = event_info.get("method_strength", 0)
                    event_data_str = f"Auth attempt: {'Success' if success else 'Failed'} (method strength: {method})"
                elif event_subtype == "keyguard_dismissed":
                    event_data_str = "Keyguard dismissed"
                elif event_subtype == "keyguard_secured":
                    event_data_str = "Device locked"
                elif event_subtype == "keyguard_disabled_features_set":
                    admin = event_info.get("admin_package", "")
                    features = event_info.get("disabled_features", "")
                    event_data_str = (
                        f"Keyguard features disabled by {admin}: {features}"
                    )

                # Key events
                elif event_subtype == "key_generated":
                    success = event_info.get("success", False)
                    key_id = event_info.get("key_id", "unknown")
                    uid = event_info.get("uid", "")
                    event_data_str = f"Key {'generated' if success else 'generation failed'}: {key_id} (UID: {uid})"
                elif event_subtype == "key_destruction":
                    success = event_info.get("success", False)
                    key_id = event_info.get("key_id", "unknown")
                    uid = event_info.get("uid", "")
                    event_data_str = f"Key {'destroyed' if success else 'destruction failed'}: {key_id} (UID: {uid})"
                elif event_subtype == "key_import":
                    success = event_info.get("success", False)
                    key_id = event_info.get("key_id", "unknown")
                    event_data_str = (
                        f"Key {'imported' if success else 'import failed'}: {key_id}"
                    )
                elif event_subtype == "key_integrity_violation":
                    key_id = event_info.get("key_id", "unknown")
                    event_data_str = f"Key integrity violation: {key_id}"

                # Certificate events
                elif event_subtype == "cert_authority_installed":
                    success = event_info.get("success", False)
                    subject = event_info.get("subject", "unknown")
                    event_data_str = f"Cert {'installed' if success else 'install failed'}: {subject}"
                elif event_subtype == "cert_authority_removed":
                    success = event_info.get("success", False)
                    subject = event_info.get("subject", "unknown")
                    event_data_str = (
                        f"Cert {'removed' if success else 'removal failed'}: {subject}"
                    )
                elif event_subtype == "cert_validation_failure":
                    reason = (
                        event_info if isinstance(event_info, str) else str(event_info)
                    )
                    event_data_str = f"Certificate validation failure: {reason}"
                elif event_subtype == "crypto_self_test_completed":
                    if isinstance(event_info, dict):
                        success = event_info.get("success", False)
                    else:
                        success = event_info == 1
                    event_data_str = (
                        f"Crypto self test: {'passed' if success else 'FAILED'}"
                    )

                # Package events
                elif event_subtype in [
                    "package_installed",
                    "package_updated",
                    "package_uninstalled",
                ]:
                    pkg_name = event_info.get("package_name", "")
                    version = event_info.get("version_code", "")
                    user_id = event_info.get("user_id", "")
                    action = event_subtype.replace("package_", "").title()
                    event_data_str = (
                        f"Package {action}: {pkg_name} (v{version}, user: {user_id})"
                    )

                # OS events
                elif event_subtype == "os_startup":
                    verified_boot = event_info.get("verified_boot_state", "")
                    dm_verity = event_info.get("dm_verity_mode", "")
                    event_data_str = f"OS startup (verified boot: {verified_boot}, dm-verity: {dm_verity})"
                elif event_subtype == "os_shutdown":
                    event_data_str = "OS shutdown"

                # Logging events
                elif event_subtype == "logging_started":
                    event_data_str = "Audit logging started"
                elif event_subtype == "logging_stopped":
                    event_data_str = "Audit logging stopped"
                elif event_subtype == "log_buffer_size_critical":
                    event_data_str = "Log buffer at 90% capacity"

                # Media events
                elif event_subtype == "media_mount":
                    mount_point = event_info.get("mount_point", "")
                    label = event_info.get("volume_label", "")
                    event_data_str = f"Media mounted: {mount_point} ({label})"
                elif event_subtype == "media_unmount":
                    mount_point = event_info.get("mount_point", "")
                    label = event_info.get("volume_label", "")
                    event_data_str = f"Media unmounted: {mount_point} ({label})"

                # Password policy events
                elif event_subtype == "password_expiration_set":
                    admin = event_info.get("admin_package", "")
                    timeout = event_info.get("timeout_ms", "")
                    event_data_str = f"Password expiration set by {admin}: {timeout}ms"
                elif event_subtype == "password_complexity_set":
                    admin = event_info.get("admin_package", "")
                    event_data_str = f"Password complexity set by {admin}"
                elif event_subtype == "password_complexity_required":
                    admin = event_info.get("admin_package", "")
                    complexity = event_info.get("complexity", "")
                    event_data_str = (
                        f"Password complexity required by {admin}: {complexity}"
                    )
                elif event_subtype == "password_history_length_set":
                    admin = event_info.get("admin_package", "")
                    length = event_info.get("length", "")
                    event_data_str = f"Password history length set by {admin}: {length}"
                elif event_subtype == "password_changed":
                    complexity = event_info.get("complexity", "")
                    user_id = event_info.get("user_id", "")
                    event_data_str = (
                        f"Password changed (complexity: {complexity}, user: {user_id})"
                    )
                elif event_subtype == "max_screen_lock_timeout_set":
                    admin = event_info.get("admin_package", "")
                    timeout = event_info.get("timeout_ms", "")
                    event_data_str = (
                        f"Max screen lock timeout set by {admin}: {timeout}ms"
                    )
                elif event_subtype == "max_password_attempts_set":
                    admin = event_info.get("admin_package", "")
                    attempts = event_info.get("max_attempts", "")
                    event_data_str = f"Max password attempts set by {admin}: {attempts}"

                # Remote lock and wipe events
                elif event_subtype == "remote_lock":
                    admin = event_info.get("admin_package", "")
                    event_data_str = f"Device remotely locked by {admin}"
                elif event_subtype == "wipe_failure":
                    event_data_str = "Device wipe failed"

                # User restriction events
                elif event_subtype == "user_restriction_added":
                    admin = event_info.get("admin_package", "")
                    restriction = event_info.get("restriction", "")
                    event_data_str = f"User restriction added by {admin}: {restriction}"
                elif event_subtype == "user_restriction_removed":
                    admin = event_info.get("admin_package", "")
                    restriction = event_info.get("restriction", "")
                    event_data_str = (
                        f"User restriction removed by {admin}: {restriction}"
                    )

                # WiFi events
                elif event_subtype == "wifi_connection":
                    bssid = event_info.get("bssid", "")
                    event_type = event_info.get("event_type", "")
                    reason = event_info.get("reason", "")
                    event_data_str = f"WiFi connection: {event_type} (BSSID: {bssid})"
                    if reason:
                        event_data_str += f" - {reason}"
                elif event_subtype == "wifi_disconnection":
                    bssid = event_info.get("bssid", "")
                    reason = event_info.get("reason", "")
                    event_data_str = f"WiFi disconnection (BSSID: {bssid})"
                    if reason:
                        event_data_str += f" - {reason}"

                # Bluetooth events
                elif event_subtype == "bluetooth_connection":
                    mac = event_info.get("mac_address", "")
                    success = event_info.get("success", False)
                    reason = event_info.get("reason", "")
                    event_data_str = f"Bluetooth {'connected' if success else 'connection failed'}: {mac}"
                    if reason:
                        event_data_str += f" - {reason}"
                elif event_subtype == "bluetooth_disconnection":
                    mac = event_info.get("mac_address", "")
                    reason = event_info.get("reason", "")
                    event_data_str = f"Bluetooth disconnected: {mac}"
                    if reason:
                        event_data_str += f" - {reason}"

                # Camera policy event
                elif event_subtype == "camera_policy_set":
                    admin = event_info.get("admin_package", "")
                    disabled = event_info.get("disabled", False)
                    event_data_str = (
                        f"Camera {'disabled' if disabled else 'enabled'} by {admin}"
                    )

                # Backup service event
                elif event_subtype == "backup_service_toggled":
                    admin = event_info.get("admin_package", "")
                    enabled = event_info.get("enabled", False)
                    event_data_str = f"Backup service {'enabled' if enabled else 'disabled'} by {admin}"

                # NFC events
                elif event_subtype == "nfc_enabled":
                    event_data_str = "NFC enabled"
                elif event_subtype == "nfc_disabled":
                    event_data_str = "NFC disabled"

                else:
                    event_data_str = (
                        f"{SECURITY_EVENT_TAGS.get(event_subtype, {}).get('name', event_subtype)}: "
                        f"{event_info}"
                    )
            else:
                event_data_str = f"{event_subtype}: {event_info}"

        if not event_subtype:
            event_subtype = "unknown"
            event_data_str = str(record)

        return {
            "timestamp": record.get("timestamp"),
            "module": self.__class__.__name__,
            "event": event_subtype,
            "data": event_data_str,
        }

    def process_event(self, event_data: dict) -> None:
        """Process a security event and add it to results."""
        # Convert event_time to ISO format
        # Security events use nanoseconds since epoch
        event_time = event_data.get("event_time")
        if event_time:
            # Convert nanoseconds to seconds
            event_data["timestamp"] = self._localize_timestamp(
                event_time / 1_000_000_000.0
            )
        else:
            event_data["timestamp"] = None

        # Track event type statistics, including future tags unknown to MVT.
        event_tag = self._get_event_tag(event_data)
        if event_tag:
            self.event_type_counts[event_tag] = (
                self.event_type_counts.get(event_tag, 0) + 1
            )

        self.results.append(event_data)

    def run(self) -> None:
        """Extract and analyze security events from intrusion logs."""
        if not self.target_path:
            self.log.error("No target path specified")
            return

        self.collect_txt(self.target_path)
        self.parse_collected_txt("security_event")

        self.log.info("Identified %d security events", len(self.results))

        # Log event type breakdown
        if self.event_type_counts:
            self.log.info("Security event breakdown:")
            for event_type, count in sorted(
                self.event_type_counts.items(), key=lambda x: x[1], reverse=True
            ):
                event_name = SECURITY_EVENT_TAGS.get(event_type, {}).get(
                    "name", event_type
                )
                self.log.info("  - %s: %d", event_name, count)

            unknown_event_types = sorted(
                event_type
                for event_type in self.event_type_counts
                if event_type not in SECURITY_EVENT_TAGS
            )
            if unknown_event_types:
                self.log.warning(
                    "Found unknown intrusion logging security event type(s): %s. "
                    "Please open an issue on GitHub so MVT can add support for them.",
                    ", ".join(unknown_event_types),
                )
