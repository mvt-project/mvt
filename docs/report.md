# HTML Report

After a check, MVT can turn its results folder into a single HTML file that is easier to read and share than the JSON and CSV files it contains:

```bash
mvt-ios report /path/to/iphone/output/
```

```bash
mvt-android report /path/to/android/output/
```

The report is written to `report.html` inside the results folder. Use `--output` to write it somewhere else.

The report shows:

- a summary of the detections by severity;
- the device model and OS version, the indicator files that were loaded and the SHA-256 hash of `info.json`;
- a chart of the events over time, with the detections placed on it;
- each detection with the indicator it matched, the full record and the events recorded around the same time;
- the timeline, which can be searched and filtered by source or by time range.

The report is built only from the files in the results folder, so it can be generated again at any time, for example after running `check-iocs` with new indicators. It embeds everything it needs and loads nothing from the network, so it can be opened offline.

!!! warning
    The report contains records extracted from the device, such as messages and browsing history. Share it only with people you trust. Serial numbers, IMEI and phone numbers from the device information are left out, but the records themselves are included as they are.
