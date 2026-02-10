# Check over ADB

In order to check an Android device over the [Android Debug Bridge (adb)](https://developer.android.com/studio/command-line/adb) you will first need to install [Android SDK Platform Tools](https://developer.android.com/studio/releases/platform-tools). If you have installed [Android Studio](https://developer.android.com/studio/) you should already have access to `adb` and other utilities.

While many Linux distributions already package Android Platform Tools (for example `android-platform-tools-base` on Debian), it is preferable to install the most recent version from the official website. Packaged versions might be outdated and incompatible with most recent Android handsets.

Next you will need to enable debugging on the Android device you are testing. [Please follow the official instructions on how to do so.](https://developer.android.com/studio/command-line/adb)

## Connecting over USB

The easiest way to check the device is over a USB transport. You will need to have USB debugging enabled and the device plugged into your computer. If everything is configured appropriately you should see your device when launching the command `adb devices`.

Now you can try launching MVT with:

```bash
mvt-android check-adb --output /path/to/results
```

!!! warning
    The `check-adb` command is deprecated and will be removed in a future release.
    Whenever possible, prefer acquiring device data using the AndroidQF project (https://github.com/mvt-project/androidqf/) and then analyze those acquisitions with MVT.

    Running `mvt-android check-adb` will also emit a runtime deprecation warning advising you to migrate to AndroidQF.

If you have previously started an adb daemon MVT will alert you and require you to kill it with `adb kill-server` and relaunch the command.

!!! warning

    The `mvt-android check-adb` command has been deprecated and removed from MVT.

The ability to analyze Android devices over ADB (`mvt-android check-adb`) has been removed from MVT due to several technical and forensic limitations.

## Reasons for Deprecation

1. **Inconsistent Data Collection Across Devices**
   Android devices vary significantly in their system architecture, security policies, and available diagnostic logs. This inconsistency makes it difficult to ensure that MVT can reliably collect necessary forensic data across all devices.

2. **Incomplete Forensic Data Acquisition**
   The `check-adb` command did not retrieve a full forensic snapshot of all available data on the device. For example, critical logs such as the **full bugreport** were not systematically collected, leading to potential gaps in forensic analysis. This can be a serious problem in scenarios where the analyst only had one time access to the Android device.

4. **Code Duplication and Difficulty Ensuring Consistent Behavior Across Sources**
    Similar forensic data such as "dumpsys" logs were being loaded and parsed by MVT's ADB, AndroidQF and Bugreport commands. Multiple modules were needed to handle each source format which created duplication leading to inconsistent
    behavior and difficulties in maintaining the code base.

5. **Alignment with iOS Workflow**
   MVT’s forensic workflow for iOS relies on pre-extracted artifacts, such as iTunes backups or filesystem dumps, rather than preforming commands or interactions directly on a live device. Removing the ADB functionality ensures a more consistent methodology across both Android and iOS mobile forensic.

## Alternative: Using AndroidQF for Forensic Data Collection

To replace the deprecated ADB-based approach, forensic analysts should use [AndroidQF](https://github.com/mvt-project/androidqf) for comprehensive data collection, followed by MVT for forensic analysis. The workflow is outlined in the MVT [Android methodology](./methodology.md)
