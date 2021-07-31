# Indicators of Compromise (IOCs)

MVT uses [Structured Threat Information Expression (STIX)](https://oasis-open.github.io/cti-documentation/stix/intro.html) files to identify potential traces of compromise.

These indicators of compromise are contained in a file with a particular structure of [JSON](https://en.wikipedia.org/wiki/JSON) with the `.stix2` or `.json` extensions.

For example, after extracting iOS forensics data from an iPhone using `mvt-ios check-backup` or `mvt-ios check-fs`, you might run:

```bash
mvt-ios check-iocs --iocs ~/iocs/wintermute.stix2 /path/to/iphone/output/
```

Or, with data from an android backup:

```bash
mvt-android check-backup --iocs ~/iocs/wintermute.stix2 /path/to/android/backup/
```

If you're looking for indicators of compromise for a specific piece of malware or adversary, please ask investigators or anti-malware researchers who have the relevant expertise for a STIX file.

## Known repositories of STIX IOCs

We currently know of the following STIX-formatted IOCs:

- [Cyber Threat Intelligence Technical Committee's sample STIX 2.1 Threat reports](https://oasis-open.github.io/cti-documentation/stix/examples#stix-21-threat-reports): the "JSON representation" column offers sample STIX-formatted IOCs for:
  - [APT1](https://en.wikipedia.org/wiki/APT1) ([STIX](https://oasis-open.github.io/cti-documentation/examples/example_json/apt1.json)), 
  - [Poison Ivy](https://www.cyber.nj.gov/threat-center/threat-profiles/trojan-variants/poison-ivy/) ([STIX](https://oasis-open.github.io/cti-documentation/examples/example_json/poisonivy.json)), and
  - [IMDDOS](https://www.coresecurity.com/publication/imddos-botnet-discovery-and-analysis)([STIX](https://gist.github.com/rjsmitre/79775df68b0d1c7c0985b4fe7f115586/raw/d5d2a3e7b4ae52ff7153a8b7b5b57dd066611803/imddos.json))
- The [Amnesty International investigations repository](https://github.com/AmnestyTech/investigations) contains STIX-formatted IOCs for:
  - [Pegasus](https://en.wikipedia.org/wiki/Pegasus_(spyware))

Please [open an issue](https://github.com/mvt-project/mvt/issues/) to suggest new sources of STIX-formatted IOCs.
