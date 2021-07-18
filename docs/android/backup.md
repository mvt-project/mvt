# Checking SMSs from Android backup

Some attacks against Android phones are done by sending malicious links by SMS. The Android backup feature does not allow to gather much information that can be interesting for a forensic analysis, but it can be used to extract SMSs and check them with MVT.

To do so, you need to connect your Android device to your computer. You will then need to [enable USB debugging](https://developer.android.com/studio/debug/dev-options#enable>) on the Android device.

If this is the first time you connect to this device, you will need to approve the authentication keys through a prompt that will appear on your Android device.

Then you can use adb to extract the backup for SMS only with the following command:

```bash
adb backup com.android.providers.telephony
```

You will need to approve the backup on the phone and potentially enter a password to encrypt the backup. The backup will then be stored in a file named `backup.ab`.

You will need to use [Android Backup Extractor](https://github.com/nelenkov/android-backup-extractor) to convert it to a readable file format. Make sure that java is installed on your system and use the following command:
```bash
java -jar ~/Download/abe.jar unpack backup.ab backup.tar
tar xvf backup.tar
```

(If the backup is encrypted, the password will be asked by Android Backup Extractor).

You can then extract SMSs containing links with MVT:

```bash
$ mvt-android check-backup --output sms .
16:18:38 INFO     [mvt.android.cli] Checking ADB backup located at: .
         INFO     [mvt.android.modules.backup.sms] Running module SMS...
         INFO     [mvt.android.modules.backup.sms] Processing SMS backup
                  file at ./apps/com.android.providers.telephony/d_f/000
                  000_sms_backup
16:18:39 INFO     [mvt.android.modules.backup.sms] Extracted a total of
                  64 SMS messages containing links
```

Through the `--iocs` argument you can specify a [STIX2](https://oasis-open.github.io/cti-documentation/stix/intro) file defining a list of malicious indicators to check against the records extracted from the backup by mvt. Any matches will be highlighted in the terminal output.
