# Backup with libimobiledevice

If you have correctly [installed libimobiledevice](../install.md) you can easily generate an iTunes backup using the `idevicebackup2` tool included in the suite. First, you might want to ensure that backup encryption is enabled (**note: encrypted backup contain more data than unencrypted backups**):

```bash
idevicebackup2 -i backup encryption on
```

Note that if a backup password was previously set on this device, you might need to use the same or change it. You can try changing password using `idevicebackup2 -i backup changepw`, or by turning off encryption (`idevicebackup2 -i backup encryption off`) and turning it back on again.

If that fails, as a last resort you can try resetting the password by [resetting all the settings through the iPhone's Settings app](https://support.apple.com/en-us/HT205220), via `Settings » General » Reset » Reset All Settings`.  Note that resetting the settings through the iPhone's Settings app may wipe some of the files that contain useful forensic traces, so try to reset the device's password using `idevicebackup2` as described above first.

Once ready, you can proceed performing the backup:

```bash
idevicebackup2 backup --full /path/to/backup/
```
