# Indicators of Compromise (IOCs)

MVT uses [Structured Threat Information Expression (STIX)](https://oasis-open.github.io/cti-documentation/stix/intro.html) files to identify potential traces of compromise.

These indicators of compromise are contained in a file with a particular structure of [JSON](https://en.wikipedia.org/wiki/JSON) with the `.stix2` or `.json` extensions.

You can indicate a path to a STIX2 indicators file when checking iPhone backups or filesystem dumps. For example:

```bash
mvt-ios check-backup --iocs ~/ios/malware.stix2 --output /path/to/iphone/output /path/to/backup
```

Or, with data from an Android backup:

```bash
mvt-android check-backup --iocs ~/iocs/malware.stix2 /path/to/android/backup/
```

After extracting forensics data from a device, you are also able to compare it with any STIX2 file you indicate:

```bash
mvt-ios check-iocs --iocs ~/iocs/malware.stix2 /path/to/iphone/output/
```

If you're looking for indicators of compromise for a specific piece of malware or adversary, please ask investigators or anti-malware researchers who have the relevant expertise for a STIX file.

## Known repositories of STIX2 IOCs

- The [Amnesty International investigations repository](https://github.com/AmnestyTech/investigations) contains STIX-formatted IOCs for:
    - [Pegasus](https://en.wikipedia.org/wiki/Pegasus_(spyware)) ([STIX2](https://raw.githubusercontent.com/AmnestyTech/investigations/master/2021-07-18_nso/pegasus.stix2))

Please [open an issue](https://github.com/mvt-project/mvt/issues/) to suggest new sources of STIX-formatted IOCs.
