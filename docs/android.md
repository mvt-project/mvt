# Checking an Android Device

In order to use `mvt-android` you need to connect your Android device to your computer. You will then need to [enable USB debugging](https://developer.android.com/studio/debug/dev-options#enable>) on the Android device.

If this is the first time you connect to this device, you will need to approve the authentication keys through a prompt that will appear on your Android device.

Now you can launch `mvt-android` and specify the `download-apks` command and the path to the folder where you want to store the extracted data:

```bash
mvt-android download-apks --output /path/to/folder
```

Optionally, you can decide to enable lookups of the SHA256 hash of all the extracted APKs on [VirusTotal](https://www.virustotal.com) and/or [Koodous](https://www.koodous.com). While these lookups do not provide any conclusive assessment on all of the extracted APKs, they might highlight any known malicious ones:

```bash
mvt-android download-apks --output /path/to/folder --virustotal
mvt-android download-apks --output /path/to/folder --koodous
```

Or, to launch all available lookups::

```bash
mvt-android download-apks --output /path/to/folder --all-checks
```
