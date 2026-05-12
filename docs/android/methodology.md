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

## Android Intrusion Logs

On devices where the user has opted into Android's [**Advanced Protection Mode**](https://support.google.com/android/answer/16339980) and turned on the optional Intrusion Logging featrue, Android can create and archive structured *Intrusion Logs* in an encrypted format. These logs record DNS queries, outbound network connections, process starts, ADB activity and other security-relevant events, and are a high-fidelity complement to the rest of an AndroidQF acquisition. The logs are generated on-device and encrypted before being stored in the Google account associated with the device. The encryption key is protected by the user device PIN. The intrusion log data is not accessible to Google.

AndroidQF will prompt the user to download, decrypt and collect device intrusion logs as part of an acquisition. When they are present, `mvt-android check-androidqf` will automatically run the intrusion-log checks alongside the other AndroidQF modules — no extra command is required. This is the recommended workflow for Android forensic analysis with MVT.

For cases where intrusion logs were collected outside of an AndroidQF acquisition, the standalone `mvt-android check-intrusion-logs` command can analyse them directly. See [Check Android Intrusion Logs](intrusion_logs.md) for details, and the [feature announcment from Amnesty International's Security Lab](https://securitylab.amnesty.org/latest/2026/05/android-intrusion-logging-as-a-new-source-of-data-for-consensual-forensic-analysis/) for background on the data source.

## Android Debug Bridge analysis removed

The ability to analyze Android devices directly over ADB has been removed from MVT. Direct extraction of data from ADB was error-prone and frequently resulted in inconsistent data collection between ADB and AndroidQF acquisitions. Use AndroidQF for device acquisition and `mvt-android check-androidqf` for analysis.

## Check an Android Backup (SMS messages)

Although Android backups are becoming deprecated, it is still possible to generate one. Unfortunately, because apps these days typically favor backup over the cloud, the amount of data available is limited.

The `mvt-android check-androidqf` command will automatically check an Android backup and SMS messages if an SMS backup is included in the AndroidQF extraction.

The  `mvt-android check-backup` command can also be used directly with an Android backup file.
