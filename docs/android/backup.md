# Check an Android Backup (SMS messages)

Android supports generating a backup archive of all the installed applications which supports it. However, over the years this functionality has been increasingly abandoned in favor of enabling users to remotely backup their personal data over the cloud. App developers can therefore decide to opt out from allowing the apps' data from being exported locally.

At the time of writing, the Android Debug Bridge (adb) command to generate backups is still available but marked as deprecated.

That said, most versions of Android should still allow to locally backup SMS messages, and since messages are still a prime vehicle for phishing and malware attacks, you might still want to take advantage of this functionality while it is supported.

## Generate a backup

Because `mvt-android check-backup` currently only supports checking SMS messages, you can indicate to backup only those:

```bash
adb backup com.android.providers.telephony
```

In case you nonetheless wish to take a full backup, you can do so with

```bash
adb backup -all
```

## Unpack the backup

In order to reliable unpack th [Android Backup Extractor (ABE)](https://github.com/nelenkov/android-backup-extractor) to convert it to a readable file format. Make sure that java is installed on your system and use the following command:

```bash
java -jar ~/path/to/abe.jar unpack backup.ab backup.tar
tar xvf backup.tar
```

If the backup is encrypted, ABE will prompt you to enter the password.

## Check the backup

You can then extract SMSs containing links with MVT:

```bash
$ mvt-android check-backup --output /path/to/results/ /path/to/backup/
16:18:38 INFO     [mvt.android.cli] Checking ADB backup located at: .
         INFO     [mvt.android.modules.backup.sms] Running module SMS...
         INFO     [mvt.android.modules.backup.sms] Processing SMS backup file at /path/to/backup/apps/com.android.providers.telephony/d_f/000000_sms_backup
16:18:39 INFO     [mvt.android.modules.backup.sms] Extracted a total of
                  64 SMS messages containing links
```

Through the `--iocs` argument you can specify a [STIX2](https://oasis-open.github.io/cti-documentation/stix/intro) file defining a list of malicious indicators to check against the records extracted from the backup by mvt. Any matches will be highlighted in the terminal output.
