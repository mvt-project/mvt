# Check Android Intrusion Logs

Recent versions of Android can produce structured *Intrusion Logs* — newline-delimited JSON records derived from the platform's [SecurityLog API](https://developer.android.com/reference/android/app/admin/SecurityLog). Intrusion Logging is offered as a new option under Android's **Advanced Protection Mode**, which users can opt into on their device; no MDM or device-policy configuration is required. When enabled, these logs provide a high-fidelity record of process starts, DNS queries, outbound network connections, ADB activity, keyguard events, and other security-relevant operations. The initial Intrusion Logging feature was released for Android 16 in May 2026. The feature and supported events are likely to be expanded over time.

The introduction and forensic uses of this data source are described in the Amnesty International Security Lab announcement: [Android Intrusion Logging as a new source of data for consensual forensic analysis](https://securitylab.amnesty.org/latest/2026/05/android-intrusion-logging-as-a-new-source-of-data-for-consensual-forensic-analysis/).

## Collection with AndroidQF

[AndroidQF](https://github.com/mvt-project/androidqf) supports intrusion-log collection during Android acquisitions. It prompts for log collection and writes the collected files into an `intrusion-logs/` subdirectory of the acquisition output.

During analysis with `mvt-android check-androidqf`, MVT automatically detects the `intrusion-logs/` directory and includes intrusion-log checks in the acquisition analysis:

```bash
mvt-android check-androidqf --output /path/to/results/ /path/to/androidqf-output/
```

The device timezone is read from the AndroidQF acquisition (`getprop.txt`) and applied to event timestamps automatically.

## Standalone command: `check-intrusion-logs`

The `mvt-android check-intrusion-logs` command analyses a set of intrusion-log files independently of an AndroidQF acquisition. Its input can consist of logs collected through another method or the intrusion logs from an existing acquisition.

## Log format

`check-intrusion-logs` accepts either:

- a **directory** containing one or more `.txt` files (recursively), or
- a **`.zip` archive** containing such `.txt` files (nested `.zip` archives are also walked).

Each `.txt` file is expected to contain newline-delimited JSON, with one JSON object per line. Each object wraps a single event under a top-level key indicating its type, for example:

```json
{"dns_event": {"event_time": 1746979200000, "hostname": "example.com", "ip_addresses": ["93.184.216.34"], "package_name": "com.example.app"}}
{"connect_event": {"event_time": 1746979201000, "ip_address": "93.184.216.34", "port": 443, "package_name": "com.example.app"}}
{"security_event": {"event_id": 0, "event_time": 1746979202000000000, "app_process_start": {"process": "com.example.app", "uid": 10000, "pid": 1234}}}
```

The top-level keys `dns_event`, `connect_event`, and `security_event` identify DNS resolutions, outbound network connections, and security events respectively. Network-event `event_time` values are in milliseconds since the Unix epoch; security-event values are in nanoseconds.

Within a `security_event`, a named subevent such as `app_process_start` identifies the operation and contains its payload. The `event_id` field is event metadata, separate from the Android `SecurityLog` tag ID. The exporter assigns the JSON subevent names, which can differ from the platform's Java constants and raw `security_*` event-log names.

Examples of exported security subevents and their payload fields include:

| Exported security subevent | Payload fields |
| --- | --- |
| `adb_shell_cmd` | `command` |
| `adb_sync_recv_file`, `adb_sync_send_file` | `path` |
| `key_generated`, `key_imported`, `key_destruction` | `success`, `key_id`, `uid` |
| `os_startup` | `boot_state`, `verity_mode` |
| `user_restriction_added`, `user_restriction_removed` | `package`, `admin_user`, `restriction` |

The `command` field records an ADB shell command, while `path` records the file path involved in an ADB transfer. Key events contain a JSON boolean `success` value, the key identifier, and the UID associated with the operation. Key imports appear as `key_imported`, and key destruction appears as `key_destruction`. Startup events contain the verified boot state and dm-verity mode; user-restriction events identify the administrator package, administrator user, and restriction.

These names and field types are present in the Pixel export attached to [issue #971](https://github.com/mvt-project/mvt/issues/971). The [Amnesty technical briefing](https://securitylab.amnesty.org/latest/2026/05/android-intrusion-logging-as-a-new-source-of-data-for-consensual-forensic-analysis/) also includes examples of `adb_shell_cmd` and `adb_sync_recv_file`. The examples describe those exports; event names and payload fields may differ between exporter versions.

Identical events that appear across multiple overlapping log files (e.g. daily rotations) are de-duplicated on a first-seen basis.

## Analysis commands

```bash
mvt-android check-intrusion-logs --output /path/to/results/ /path/to/intrusion-logs/
```

A `.zip` archive can be passed directly in place of the directory:

```bash
mvt-android check-intrusion-logs --output /path/to/results/ /path/to/intrusion-logs.zip
```

### Options

| Option | Description |
| --- | --- |
| `-i, --iocs PATH` | Path to a STIX2 indicator file. May be passed multiple times. |
| `-o, --output PATH` | Directory where JSON results and the timeline CSV will be written. |
| `-l, --list-modules` | Lists the available intrusion-log modules and exits. |
| `-m, --module NAME` | Limits analysis to a single module (e.g. `DnsEvent`). |
| `-t, --timezone TZ` | IANA timezone name for the device (e.g. `Europe/Paris`). When set, event timestamps are converted to the device's local time instead of UTC. |
| `-v, --verbose` | Enables verbose logging. Retained for compatibility; the global `mvt-android --verbose` option also controls verbosity. |

## Modules

The command runs the following modules over the parsed events:

- **`DnsEvent`** — DNS resolution events. Hostnames and resolved IP addresses are checked against domain indicators, and the requesting `package_name` is checked against app-identifier indicators.
- **`ConnectEvent`** — Outbound network connection events. Destination IPs (with localhost addresses skipped) are checked against domain indicators, and `package_name` is checked against app-identifier indicators.
- **`SecurityEvent`** — Security log events identified by named JSON subevents (e.g. `app_process_start`, `adb_shell_cmd`, `keyguard_dismissed`, `os_startup`, `cert_*` events). These are surfaced in the timeline to help reconstruct device activity around suspected events.

All three modules share a single pre-parsing pass over the input, so the log files are parsed once for the analysis.

## Results

A successful IOC match raises a `CRITICAL` alert that includes the matched indicator, the offending event, and the event timestamp. Alerts are summarised at the end of the run and persisted alongside the per-module JSON results.

When `--timezone` is provided, timestamps in the timeline and JSON output reflect the device's local wall-clock time. Otherwise timestamps are in UTC, consistent with the rest of MVT.

## Limitations

- Intrusion logs cover activity recorded while the optional Intrusion Logging feature is enabled under Android's Advanced Protection Mode. MVT analyses the collected files; it does not enable logging on the device.
- As with all IOC-based analysis, public indicators alone are not sufficient to conclude that a device is uncompromised. The [Indicators of Compromise](../iocs.md) page describes the scope of indicator-based analysis.
