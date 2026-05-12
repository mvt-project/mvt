# Check Android Intrusion Logs

Recent versions of Android can produce structured *Intrusion Logs* — newline-delimited JSON records derived from the platform's [SecurityLog API](https://developer.android.com/reference/android/app/admin/SecurityLog). Intrusion Logging is offered as a new option under Android's **Advanced Protection Mode**, which users can opt into on their device; no MDM or device-policy configuration is required. When enabled, these logs provide a high-fidelity record of process starts, DNS queries, outbound network connections, ADB activity, keyguard events, and other security-relevant operations. The initial Intrusion Logging feature was released for Android 16 in May 2026. The feature and supported events is likely to be expanded over time.

For background on how this data source was introduced and why it is forensically valuable, see the Amnesty International Security Lab announcement: [Android Intrusion Logging as a new source of data for consensual forensic analysis](https://securitylab.amnesty.org/latest/2026/05/android-intrusion-logging-as-a-new-source-of-data-for-consensual-forensic-analysis/).

## Recommended workflow: collect with AndroidQF

[AndroidQF](https://github.com/mvt-project/androidqf) is the recommended way to acquire data from an Android device for analysis with MVT. During acquisition AndroidQF will prompt the user to also collect intrusion logs from the device, and writes them into an `intrusion-logs/` subdirectory of the acquisition output.

When you analyse such an acquisition with `mvt-android check-androidqf`, MVT automatically detects the `intrusion-logs/` directory and runs the same intrusion-log checks described below — there is no need to invoke a separate command:

```bash
mvt-android check-androidqf --output /path/to/results/ /path/to/androidqf-output/
```

The device timezone is read from the AndroidQF acquisition (`getprop.txt`) and applied to event timestamps automatically.

## Standalone command: `check-intrusion-logs`

The `mvt-android check-intrusion-logs` command runs the intrusion-log analysis directly against a set of log files. Prefer the AndroidQF workflow above; use the standalone command when the intrusion logs were collected outside of an AndroidQF acquisition, or when re-analysing only a set of intrusion logs.

## Expected input

`check-intrusion-logs` accepts either:

- a **directory** containing one or more `.txt` files (recursively), or
- a **`.zip` archive** containing such `.txt` files (nested `.zip` archives are also walked).

Each `.txt` file is expected to contain newline-delimited JSON, with one JSON object per line. Each object wraps a single event under a top-level key indicating its type, for example:

```json
{"dns_event": {"event_time": 1746979200000, "hostname": "example.com", "ip_addresses": ["93.184.216.34"], "package_name": "com.example.app"}}
{"connect_event": {"event_time": 1746979201000, "ip_address": "93.184.216.34", "port": 443, "package_name": "com.example.app"}}
{"security_event": {"event_time": 1746979202000, "tag": 210005, "data": ["..."]}}
```

Identical events that appear across multiple overlapping log files (e.g. daily rotations) are de-duplicated on a first-seen basis.

## Running the analysis

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
| `-l, --list-modules` | List the available intrusion-log modules and exit. |
| `-m, --module NAME` | Run a single module (e.g. `DnsEvent`) instead of all of them. |
| `-t, --timezone TZ` | IANA timezone name for the device (e.g. `Europe/Paris`). When set, event timestamps are converted to the device's local time instead of UTC. |
| `-v, --verbose` | Verbose logging. |

## Modules

The command runs the following modules over the parsed events:

- **`DnsEvent`** — DNS resolution events. Hostnames and resolved IP addresses are checked against domain indicators, and the requesting `package_name` is checked against app-identifier indicators.
- **`ConnectEvent`** — Outbound network connection events. Destination IPs (with localhost addresses skipped) are checked against domain indicators, and `package_name` is checked against app-identifier indicators.
- **`SecurityEvent`** — Security log events keyed by Android `SecurityLog` tag IDs (e.g. `app_process_start`, `adb_shell_cmd`, `keyguard_dismissed`, `os_startup`, `cert_*` events). These are surfaced in the timeline to help reconstruct device activity around suspected events.

All three modules share a single pre-parsing pass over the input, so adding more modules in the future does not multiply I/O cost. Additional modules will be added in the future to support new event types which are generated by the Intrusion Logging feature.

## Interpreting results

A successful IOC match raises a `CRITICAL` alert that includes the matched indicator, the offending event, and the event timestamp. Alerts are summarised at the end of the run and persisted alongside the per-module JSON results.

When `--timezone` is provided, timestamps in the timeline and JSON output reflect the device's local wall-clock time. Otherwise timestamps are in UTC, consistent with the rest of MVT.

## Limitations

- This page assumes the intrusion logs have already been collected from the device. The recommended collection path is via AndroidQF (see above); intrusion logging itself must have been enabled on the device beforehand by opting into Android's Advanced Protection mode and also enabling the optional Intrusion Logging feature (see the [Amnesty blog post](https://securitylab.amnesty.org/latest/2026/05/android-intrusion-logging-as-a-new-source-of-data-for-consensual-forensic-analysis/) for details).
- As with all IOC-based analysis, public indicators alone are not sufficient to conclude that a device is uncompromised. See the [Indicators of Compromise](../iocs.md) page for context.
