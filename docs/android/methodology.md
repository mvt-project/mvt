# Methodology for Android forensic

Unfortunately Android devices provide much less observability than their iOS cousins. Android stores very little diagnostic information useful to triage potential compromises, and because of this `mvt-android` capabilities are limited as well.

However, not all is lost.

## Check installed Apps

Because malware attacks over Android typically take the form of malicious or backdoored apps, the very first thing you might want to do is to extract and verify all installed Android packages and triage quickly if there are any which stand out as malicious or which might be atypical.

While it is out of the scope of this documentation to dwell into details on how to analyze Android apps, MVT does allow to easily and automatically extract information about installed apps, download copies of them, and quickly lookup services such as [VirusTotal](https://www.virustotal.com) or [Koodous](https://www.koodous.com) which might quickly indicate known bad apps.


## Check the device over Android Debug Bridge

TODO

## Check an Android Backup (SMS messages)

TODO
