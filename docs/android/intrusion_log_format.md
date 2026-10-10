# Android Intrusion Logging JSON keys

This inventory describes the JSON exporter in Google Play services **26.32.34 (260800-968093310)**, version code **263234038**. It covers all 46 security tags handled by that implementation, plus DNS and connection events. Exporter versions may differ.

## Source provenance

The exporter was inspected in the Google Play services APK bundled with the Android SDK emulator image `system-images;android-37.2;google_apis_ps16k;x86_64`, revision 5, build `CP41.260828.004.A7`. The APK was read from `/apex/com.google.android.gmssystem/priv-app/PrebuiltGmsCoreVic@CP41.260828.004.A7/PrebuiltGmsCoreVic.apk`.

- APK SHA-256: `e088dca6adf05d438306b147011594e9a9aeed9b9ff0259a0d915546887d4e29`.
- `classes7.dex` SHA-256: `d6fa574e67f3fbd7053db4da4d7f17709ac3f19e4fd8ac0ab9748bdfc19e38ef`.
- Decompiled with JADX 1.5.6. `com.google.android.gms.intrusiondetection.service.BackupService.g()` switches on the integer SecurityLog tag and writes each JSON subevent. Its `csza` helper methods write the payload fields.
- JADX's normal mode could not reconstruct the coroutine's control flow; its simple mode exposes the switch targets and explicit `JSONObject.put()` calls. The inventory follows those calls and the helper implementations, rather than inferring exported names from AOSP logtags.

This is inspection of shipped implementation code, not published Google source or runtime observation of every event. Eighteen security event types also appear in the public Pixel export attached to [MVT issue #971](https://github.com/mvt-project/mvt/issues/971). The capture column below distinguishes these from the remaining source-verified event types.

The [Android SecurityLog API](https://developer.android.com/reference/android/app/admin/SecurityLog) and [AOSP logtag definitions](https://android.googlesource.com/platform/frameworks/base/+/99b01a65cc4c104933788b3143285ab6bae65827/core/java/android/app/admin/SecurityLogTags.logtags) establish platform semantics and raw payload layouts. Their symbolic names do not define JSON names. For example, the exporter uses `adb_shell_cmd`, `key_imported`, `key_destruction`, `media_mounted`, and `wipe_failure`.

## Event wrappers

| Top-level key | Fields | `event_time` unit |
| --- | --- | --- |
| `dns_event` | `event_id`, `event_time`, `package_name`, `hostname`, `ip_addresses`, `ip_addresses_count` | Milliseconds since Unix epoch |
| `connect_event` | `event_id`, `event_time`, `package_name`, `port`, `ip_address` | Milliseconds since Unix epoch |
| `security_event` | `event_id`, `event_time`, one named subevent from the table below | Nanoseconds since Unix epoch |

`event_id` is metadata, not the SecurityLog tag ID. The exporter converts raw success/status integers to JSON booleans for `success`, `disabled`, and `enabled`. Payload fields are omitted when the raw value has an unexpected type or is absent. Empty payloads are JSON objects (`{}`).

## Security subevents

Every row is verified against the exporter implementation identified above. A dash in the capture column means the event is absent from the issue #971 capture.

| Platform tag | JSON subevent | JSON payload fields | Capture count |
| --- | --- | --- | ---: |
| 210001 | `adb_shell_interactive` | Empty object | - |
| 210002 | `adb_shell_cmd` | `command` | 2102 |
| 210003 | `adb_sync_recv_file` | `path` | 2 |
| 210004 | `adb_sync_send_file` | `path` | 3 |
| 210005 | `app_process_start` | `process`, `start_time`, `uid`, `pid`, `seinfo`, `sha256` | 732 |
| 210006 | `keyguard_dismissed` | Empty object | 124 |
| 210007 | `keyguard_dismiss_auth_attempt` | `success`, `method_strength` | 78 |
| 210008 | `keyguard_secured` | Empty object | 26 |
| 210009 | `os_startup` | `boot_state`, `verity_mode` | 2 |
| 210010 | `os_shutdown` | Empty object | - |
| 210011 | `logging_started` | Empty object | 2 |
| 210012 | `logging_stopped` | Empty object | - |
| 210013 | `media_mounted` | `path`, `label` | - |
| 210014 | `media_unmounted` | `path`, `label` | - |
| 210015 | `log_buffer_size_critical` | Empty object | - |
| 210016 | `password_expiration_set` | `package`, `admin_user`, `target_user`, `timeout` | - |
| 210017 | `password_complexity_set` | `package`, `admin_user`, `target_user`, `length`, `quality`, `num_letters`, `num_non_letters`, `num_numeric`, `num_uppercase`, `num_lowercase`, `num_symbols` | - |
| 210018 | `password_history_length_set` | `package`, `admin_user`, `target_user`, `length` | - |
| 210019 | `max_screen_lock_timeout_set` | `package`, `admin_user`, `target_user`, `timeout` | - |
| 210020 | `max_password_attempts_set` | `package`, `admin_user`, `target_user`, `num_failures` | - |
| 210021 | `keyguard_disabled_features_set` | `package`, `admin_user`, `target_user`, `features` | - |
| 210022 | `remote_lock` | `package`, `admin_user`, `target_user` | - |
| 210023 | `wipe_failure` | Empty object | - |
| 210024 | `key_generated` | `success`, `key_id`, `uid` | 143 |
| 210025 | `key_imported` | `success`, `key_id`, `uid` | 8 |
| 210026 | `key_destruction` | `success`, `key_id`, `uid` | 57 |
| 210027 | `user_restriction_added` | `package`, `admin_user`, `restriction` | 24 |
| 210028 | `user_restriction_removed` | `package`, `admin_user`, `restriction` | 7 |
| 210029 | `cert_authority_installed` | `success`, `subject`, `target_user` | - |
| 210030 | `cert_authority_removed` | `success`, `subject`, `target_user` | - |
| 210031 | `crypto_self_test_completed` | `success` | 2 |
| 210032 | `key_integrity_violation` | `key_id`, `uid` | - |
| 210033 | `cert_validation_failure` | `reason` | - |
| 210034 | `camera_policy_set` | `package`, `admin_user`, `target_user`, `disabled` | - |
| 210035 | `password_complexity_required` | `package`, `admin_user`, `target_user`, `complexity` | - |
| 210036 | `password_changed` | `password_complexity`, `target_user` | - |
| 210037 | `wifi_connection` | `bssid`, `event_type`, `reason` | - |
| 210038 | `wifi_disconnection` | `bssid`, `reason` | - |
| 210039 | `bluetooth_connection` | `addr`, `success`, `reason` | - |
| 210040 | `bluetooth_disconnection` | `addr`, `reason` | - |
| 210041 | `package_installed` | `package_name`, `version_code`, `user_id` | 6 |
| 210042 | `package_updated` | `package_name`, `version_code`, `user_id` | 2 |
| 210043 | `package_uninstalled` | `package_name`, `version_code`, `user_id` | 5 |
| 210044 | `backup_service_toggled` | `package`, `admin_user`, `enabled` | - |
| 210045 | `nfc_enabled` | Empty object | - |
| 210046 | `nfc_disabled` | Empty object | - |

MVT keeps all input payload fields in JSON results; timeline summaries select relevant fields. Previously accepted media names (`media_mount`, `media_unmount`) and payload spellings remain supported as compatibility fallbacks. Exported field names take precedence when both forms occur.
