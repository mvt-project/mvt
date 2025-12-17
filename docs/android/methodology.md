# Methodology for Android forensic

Unfortunately Android devices provide fewer complete forensically useful datasources than their iOS cousins. Unlike iOS, the Android backup feature only provides a limited about of relevant data.

Android diagnostic logs such as *bugreport files* can be inconsistent in format and structure across different Android versions and device  vendors. The limited diagnostic information available makes it difficult to triage potential compromises, and because of this `mvt-android` capabilities are limited as well.

However, not all is lost.

## Check Android devices with AndroidQF and MVT

The [AndroidQF](https://github.com/mvt-project/androidqf) tool can be used to collect a wide range of forensic artifacts from an Android device including an Android backup, a bugreport file, and a range of system logs. MVT natively supports analyzing the generated AndroidQF output for signs of device compromise.

### Why Use AndroidQF?

- **Complete and raw data extraction**
  AndroidQF collects full forensic artifacts using an on-device forensic collection agent, ensuring that no crucial data is overlooked. The data collection does not depended on the shell environment or utilities available on the device.

- **Consistent and standardized output**
  By collecting a predefined and complete set of forensic files, AndroidQF ensures consistency in data acquisition across different Android devices.

- **Future-proof analysis**
  Since the full forensic artifacts are preserved, analysts can extract new evidence or apply updated analysis techniques without requiring access to the original device.

- **Cross-platform tool without dependencies**
  AndroidQF is a standalone Go binary which can be used to remotely collect data from an Android device without the device owner needing to install MVT or a Python environment.

### Workflow for Android Forensic Analysis with AndroidQF

With AndroidQF the analysis process is split into a separate data collection and data analysis stages.

1. **Extract Data Using AndroidQF**
  Deploy the AndroidQF forensic collector to acquire all relevant forensic artifacts from the Android device.

2. **Analyze Extracted Data with MVT**
  Use the `mvt-android check-androidqf` command to perform forensic analysis on the extracted artifacts.

By separating artifact collection from forensic analysis, this approach ensures a more reliable and scalable methodology for Android forensic investigations.

For more information, refer to the [AndroidQF project documentation](https://github.com/mvt-project/androidqf).

## Check the device over Android Debug Bridge

The ability to analyze Android devices over ADB (`mvt-android check-adb`) has been removed from MVT.

See the [Android ADB documentation](./adb.md) for more information.

## Check an Android Backup (SMS messages)

Although Android backups are becoming deprecated, it is still possible to generate one. Unfortunately, because apps these days typically favor backup over the cloud, the amount of data available is limited.

The `mvt-android check-androidqf` command will automatically check an Android backup and SMS messages if an SMS backup is included in the AndroidQF extraction.

The  `mvt-android check-backup` command can also be used directly with an Android backup file.
