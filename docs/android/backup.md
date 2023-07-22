# Check an Android Backup (SMS messages)

Android supports generating a backup archive of all the installed applications which supports it. However, over the years this functionality has been increasingly abandoned in favor of enabling users to remotely backup their personal data over the cloud. App developers can therefore decide to opt out from allowing the apps' data from being exported locally.

At the time of writing, the Android Debug Bridge (adb) command to generate backups is still available but marked as deprecated.

That said, most versions of Android should still allow to locally backup SMS messages, and since messages are still a prime vehicle for phishing and malware attacks, you might still want to take advantage of this functionality while it is supported.

## Generate a backup

Because `mvt-android check-backup` currently only supports checking SMS messages, you can indicate to backup only those:

```bash
adb backup -nocompress com.android.providers.telephony
```

In case you nonetheless wish to take a full backup, you can do so with

```bash
adb backup -nocompress -all
```

Some recent phones will enforce the utilisation of a password to encrypt the backup archive. In that case, the password will obviously be needed to extract and analyse the data later on.

## Unpack and check the backup

MVT includes a partial implementation of the Android Backup parsing, because of the implementation difference in the compression algorithm between Java and Python. The `-nocompress` option passed to adb in the section above allows to avoid this issue. You can analyse and extract SMSs from the backup directly with MVT:

```bash
$ mvt-android check-backup --output /path/to/results/ /path/to/backup.ab
14:09:45 INFO     [mvt.android.cli] Checking ADB backup located at: backup.ab
         INFO     [mvt.android.modules.backup.sms] Running module SMS...
         INFO     [mvt.android.modules.backup.sms] Processing SMS backup file at
                  apps/com.android.providers.telephony/d_f/000000_sms_backup
         INFO     [mvt.android.modules.backup.sms] Extracted a total of 64 SMS messages
```

If the backup is encrypted, MVT will prompt you to enter the password. A backup password can also be provided with the `--backup-password` command line option or through the `MVT_ANDROID_BACKUP_PASSWORD` environment variable. The same options can also be used to when analysing an encrypted backup collected through AndroidQF in the `mvt-android check-androidqf` command:

```bash
$ mvt-android check-backup --backup-password "password123" --output /path/to/results/ /path/to/backup.ab
```

Through the `--iocs` argument you can specify a [STIX2](https://oasis-open.github.io/cti-documentation/stix/intro) file defining a list of malicious indicators to check against the records extracted from the backup by MVT. Any matches will be highlighted in the terminal output.

## Alternative ways to unpack and check the backup

If you encounter an issue during the analysis of the backup, you can alternatively use [Android Backup Extractor (ABE)](https://github.com/nelenkov/android-backup-extractor) to convert it to a readable file format. Make sure that java is installed on your system and use the following command:

```bash
java -jar ~/path/to/abe.jar unpack backup.ab backup.tar
tar xvf backup.tar
```

If the backup is encrypted, ABE will prompt you to enter the password.

Alternatively, [ab-decrypt](https://github.com/joernheissler/ab-decrypt) can be used for that purpose.

You can then extract SMSs with MVT by passing the folder path as parameter instead of the `.ab` file: `mvt-android check-backup --output /path/to/results/ /path/to/backup/` (the path to backup given should be the folder containing the `apps` folder).
