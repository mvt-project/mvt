# Indicators of compromise (IOCs)

MVT uses [Structured Threat Information Expression (STIX)](https://oasis-open.github.io/cti-documentation/stix/intro.html) files to identify potential traces of compromise.

Amnesty International has released a [Technical Methodology report](https://www.amnesty.org/en/latest/research/2021/07/forensic-methodology-report-how-to-catch-nso-groups-pegasus/) which outlines how to use these indicators to hunt for Pegasus and other mobile spyware products.

## Obtaining IOCs

The [Amnesty International investigations repository](https://github.com/AmnestyTech/investigations) contains various IOCs.

```bash
git clone https://github.com/AmnestyTech/investigations.git
```

MVT uses IOC data contained in `.stix2` files, such as `pegasus.stix2`:

```
.
└── 2021-07-18_nso
    ├── README.md
    ├── domains.txt
    ├── emails.txt
    ├── files.txt
    ├── generate_stix.py
    ├── pegasus.stix2
    ├── processes.txt
    ├── v2_domains.txt
    ├── v3_domains.txt
    ├── v4_domains.txt
    └── v4_validation_domains.txt

```
