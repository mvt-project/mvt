# Backup with pymobiledevice3

After [installing pymobiledevice3](../install.md) and pairing your device, you can generate an iTunes-compatible backup using its `backup2` commands.

## Enable backup encryption

We recommend encrypted backups because they contain more data than unencrypted backups. If encryption is not already enabled, enable it with:

```bash
pymobiledevice3 backup2 encryption on 'YOUR_BACKUP_PASSWORD'
```

Replace `YOUR_BACKUP_PASSWORD` with a strong password and keep it safe: you will need it to decrypt the backup for analysis. Passwords supplied on the command line may be saved in shell history or visible to other processes.

If a backup password was previously set, use that password. To change a known password:

```bash
pymobiledevice3 backup2 change-password 'CURRENT_PASSWORD' 'NEW_PASSWORD'
```

You can also disable encryption with `pymobiledevice3 backup2 encryption off 'CURRENT_PASSWORD'` and then enable it again. Disabling encryption requires the current password; it is not a way to bypass an unknown password.

!!! warning
    If you cannot recover the password, resetting it through [Reset All Settings in the iPhone's Settings app](https://support.apple.com/en-us/HT205220) should be a last resort. Resetting settings can remove files containing useful forensic traces.

## Create a backup

Choose a new destination directory to avoid overwriting an earlier acquisition:

```bash
mkdir -p /path/to/backup/
pymobiledevice3 backup2 backup --full /path/to/backup/
```

The backup is saved in a subdirectory named after the device's UDID, such as `/path/to/backup/udid/`. Follow [Check a Backup with mvt-ios](check.md) to decrypt and analyze that directory.

For additional options, see the [pymobiledevice3 backup2 reference](https://doronz88.github.io/pymobiledevice3/cli/backup2/).
