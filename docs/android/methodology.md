# Methodology for Android forensic

Unfortunately Android devices provide much less observability than their iOS cousins. Android stores very little diagnostic information useful to triage potential compromises, and because of this `mvt-android` capabilities are limited as well.

However, not all is lost.

## Check installed Apps

Because malware attacks over Android typically take the form of malicious or backdoored apps, the very first thing you might want to do is to extract and verify all installed Android packages and triage quickly if there are any which stand out as malicious or which might be atypical.

While it is out of the scope of this documentation to dwell into details on how to analyze Android apps, MVT does allow to easily and automatically extract information about installed apps, download copies of them, and quickly lookup services such as [VirusTotal](https://www.virustotal.com) or [Koodous](https://www.koodous.com) which might quickly indicate known bad apps.


## Check the device over Android Debug Bridge

Some additional diagnostic information can be extracted from the phone using the [Android Debug Bridge (adb)](https://developer.android.com/studio/command-line/adb). `mvt-android` allows to automatically extract information including [dumpsys](https://developer.android.com/studio/command-line/dumpsys) results, details on installed packages (without download), running processes, presence of root binaries and packages, and more.


## Check an Android Backup (SMS messages)

Although Android backups are becoming deprecated, it is still possible to generate one. Unfortunately, because apps these days typically favor backup over the cloud, the amount of data available is limited. Currently, `mvt-android check-backup` only supports checking SMS messages containing links.
