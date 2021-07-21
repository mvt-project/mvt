# Downloading APKs from an Android phone

In order to use `mvt-android` you need to connect your Android device to your computer. You will then need to [enable USB debugging](https://developer.android.com/studio/debug/dev-options#enable>) on the Android device.

If this is the first time you connect to this device, you will need to approve the authentication keys through a prompt that will appear on your Android device.

Now you can launch `mvt-android` and specify the `download-apks` command and the path to the folder where you want to store the extracted data:

```bash
mvt-android download-apks --output /path/to/folder
```

Optionally, you can decide to enable lookups of the SHA256 hash of all the extracted APKs on [VirusTotal](https://www.virustotal.com) and/or [Koodous](https://koodous.com). While these lookups do not provide any conclusive assessment on all of the extracted APKs, they might highlight any known malicious ones:

```bash
mvt-android download-apks --output /path/to/folder --virustotal
mvt-android download-apks --output /path/to/folder --koodous
```

Or, to launch all available lookups::

```bash
mvt-android download-apks --output /path/to/folder --all-checks
```

# Errors:

If you receive error 

```bash
No such file or directory: '/home/{user_name}/.android/adbkey'
```

You either need to install adb or if it is installed, you have not enabled USB Debugging. To install adb, run the following commands depending on your distribution.

For Ubuntu/ Debian,

```bash
sudo apt-get install android-tools-adb
```

For Fedora/ SUSE-based Linux, 

```bash
sudo yum install android-tools
```

To check if this has been installed correctly, connect your phone to the computer using USB cable, and run 
```bash
adb devices
```
It should display your device. 

Read [this document](https://developer.android.com/studio/debug/dev-options) to enable USB debugging. On running `adb devices` for the first time, your phone will give you a warning about exchanging keys. Accept it and you're good to go. 