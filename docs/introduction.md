# Introduction

Mobile Verification Toolkit (MVT) is a collection of utilities designed to facilitate the consensual forensic acquisition of iOS and Android devices for the purpose of identifying any signs of compromise. MVT's capabilities are continuously evolving, but some of its key features include:

- Decrypt encrypted iOS backups.
- Process and parse records from numerous iOS system and apps databases, logs and system analytics.
- Extract installed applications from Android devices.
- Extract diagnostic information from Android devices through the adb protocol.
- Compare extracted records to a provided list of malicious indicators in STIX2 format.
- Generate JSON logs of extracted records, and separate JSON logs of all detected malicious traces.
- Generate a unified chronological timeline of extracted records, along with a timeline all detected malicious traces.

MVT is a forensic research tool intended for technologists and investigators. Using it requires understanding the basics of forensic analysis and using command-line tools. MVT is not intended for end-user self-assessment. If you are concerned with the security of your device please seek expert assistance.

## Indicators of Compromise

MVT supports using [indicators of compromise (IOCs)](https://github.com/mvt-project/mvt-indicators) to scan mobile devices for potential traces of targeting or infection by known spyware campaigns. This includes IOCs published by [Amnesty International](https://github.com/AmnestyTech/investigations/) and other research groups.

!!! warning
    Public indicators of compromise are insufficient to determine that a device is "clean", and not targeted with a particular spyware tool. Reliance on public indicators alone can miss recent forensic traces and give a false sense of security.

    Reliable and comprehensive digital forensic support and triage requires access to non-public indicators, research and threat intelligence.

    Such support is available to civil society through [Amnesty International's Security Lab](https://securitylab.amnesty.org/get-help/?c=mvt_docs) or [Access Now’s Digital Security Helpline](https://www.accessnow.org/help/).

More information about using indicators of compromise with MVT is available in the [documentation](iocs.md).


## Consensual Forensics

While MVT is capable of extracting and processing various types of very personal records typically found on a mobile phone (such as calls history, SMS and WhatsApp messages, etc.), this is intended to help identify potential attack vectors such as malicious SMS messages leading to exploitation.

MVT's purpose is not to facilitate adversarial forensics of non-consenting individuals' devices. The use of MVT and derivative products to extract and/or analyse data originating from devices used by individuals not consenting to the procedure is explicitly prohibited in the [license](license.md).
