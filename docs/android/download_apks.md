# Downloading APKs from an Android phone

MVT allows to attempt to download all available installed packages (APKs) in order to further inspect them and potentially identify any which might be malicious in nature.

You can do so by launching the following command:

```bash
mvt-android download-apks --output /path/to/folder
```

It might take several minutes to complete.

!!! info
    MVT will likely warn you it was unable to download certain installed packages. There is no reason to be alarmed: this is typically expected behavior when MVT attempts to download a system package it has no privileges to access.

Optionally, you can decide to enable lookups of the SHA256 hash of all the extracted APKs on [VirusTotal](https://www.virustotal.com) and/or [Koodous](https://koodous.com). While these lookups do not provide any conclusive assessment on all of the extracted APKs, they might highlight any known malicious ones:

```bash
mvt-android download-apks --output /path/to/folder --virustotal
mvt-android download-apks --output /path/to/folder --koodous
```

Or, to launch all available lookups::

```bash
mvt-android download-apks --output /path/to/folder --all-checks
```

In case you have a previous extraction of APKs you want to later check against VirusTotal and Koodous, you can do so with the following arguments:

```bash
mvt-android download-apks --from-file /path/to/folder/apks.json --all-checks
```

