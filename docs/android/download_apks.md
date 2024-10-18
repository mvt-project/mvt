# Downloading APKs from an Android phone

MVT allows you to attempt to download all available installed packages (APKs) from a device in order to further inspect them and potentially identify any which might be malicious in nature.

You can do so by launching the following command:

```bash
mvt-android download-apks --output /path/to/folder
```

It might take several minutes to complete.

!!! info
    MVT will likely warn you it was unable to download certain installed packages. There is no reason to be alarmed: this is typically expected behavior when MVT attempts to download a system package it has no privileges to access.

Optionally, you can decide to enable lookups of the SHA256 hash of all the extracted APKs on [VirusTotal](https://www.virustotal.com). While these lookups do not provide any conclusive assessment on all of the extracted APKs, they might highlight any known malicious ones:

```bash
MVT_VT_API_KEY=<key> mvt-android download-apks --output /path/to/folder --virustotal
```

Please note that in order to use VirusTotal lookups you are required to provide your own API key through the `MVT_VT_API_KEY` environment variable. You should also note that VirusTotal enforces strict API usage. Be mindful that MVT might consume your hourly search quota.

In case you have a previous extraction of APKs you want to later check against VirusTotal, you can do so with the following arguments:

```bash
MVT_VT_API_KEY=<key> mvt-android download-apks --from-file /path/to/folder/apks.json --virustotal
```
