# Backup with libimobiledevice

If you have correctly [installed libimobiledevice](../install.md) you can easily generate an iTunes backup using the `idevicebackup2` tool included in the suite. First, you might want to ensure that backup encryption is enabled (**note: encrypted backup contain more data than unencrypted backups**):

```bash
idevicebackup2 backup encryption on
```

Note that if a backup password was previously set on this device, you might need to use the same or change it. You can try changing password using `idevicebackup2 backup changepw` or resetting the password by resetting only the settings through the iPhone's Settings app.

Once ready, you can proceed performing the backup:

```bash
idevicebackup2 backup --full /path/to/backup/
```
