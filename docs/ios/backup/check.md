# Check a Backup with mvt-ios

The backup might take some time. It is best to make sure the phone remains unlocked during the backup process. Afterwards, a new folder will be created under the path you specified using the UDID of the iPhone you backed up.

## Extracting and saving the decryption key (optional)

If you do not wish to enter a password every time when decrypting a backup, MVT can accept a key file instead. This key can be used with the `decrypt-backup` command.

To generate a key file, you will need your device backup and the backup password:

    $ mvt-ios extract-key --help
    Usage: mvt-ios extract-key [OPTIONS] BACKUP_PATH

      Extract decryption key from an iTunes backup

    Options:
      -p, --password TEXT  Password to use to decrypt the backup  [required]
      -k, --key-file FILE  Key file to be written (if unset, will print to STDOUT)
      --help               Show this message and exit.

You can specify the password on the command line, or omit the `-p` option to have MVT prompt for a password. The `-k` option specifies where to save the file containing the decryption key. If `-k` is omitted, MVT will display the decryption key without saving.

_Note_: This decryption key is sensitive data! Keep the file safe.

To extract the key and have MVT prompt for a password:

```bash
mvt-ios extract-key -k /path/to/save/key /path/to/backup
```

## Decrypting a backup

In case you have an encrypted backup, you will need to decrypt it first. This can be done with `mvt-ios` as well:

    $ mvt-ios decrypt-backup --help
    Usage: mvt-ios decrypt-backup [OPTIONS] BACKUP_PATH

      Decrypt an encrypted iTunes backup

    Options:
      -d, --destination TEXT  Path to the folder where to store the decrypted
                              backup  [required]

      -p, --password TEXT     Password to use to decrypt the backup (or, set
                              MVT_IOS_BACKUP_PASSWORD environment variable)
                              NOTE: This argument is mutually exclusive with
                              arguments: [key_file].

      -k, --key-file PATH     File containing raw encryption key to use to decrypt
                              the backup NOTE: This argument is mutually exclusive
                              with arguments: [password].

      --help                  Show this message and exit.

You can specify the password in the environment variable `MVT_IOS_BACKUP_PASSWORD`, or via command-line argument, or you can pass a key file.  You need to specify a destination path where the decrypted backup will be stored. If a password cannot be found and no key file is specified, MVT will ask for a password. Following is an example usage of `decrypt-backup` sending the password via an environment variable:

```bash
MVT_IOS_BACKUP_PASSWORD="mypassword" mvt-ios decrypt-backup -d /path/to/decrypted /path/to/backup
```

## Run `mvt-ios` on a Backup

Once you have a decrypted backup available for analysis you can use the `check-backup` subcommand:

    $ mvt-ios check-backup --help
    Usage: mvt-ios check-backup [OPTIONS] BACKUP_PATH

      Extract artifacts from an iTunes backup

    Options:
      -i, --iocs PATH     Path to indicators file
      -o, --output PATH   Specify a path to a folder where you want to store JSON
                          results

      -f, --fast          Avoid running time/resource consuming features
      -l, --list-modules  Print list of available modules and exit
      -m, --module TEXT   Name of a single module you would like to run instead of
                          all

      --help              Show this message and exit.

Following is a basic usage of `check-backup`:

```bash
mvt-ios check-backup --output /path/to/output/ /path/to/backup/udid/
```

This command will create a few JSON files containing the results from the extraction. If you do not specify a `--output` option, `mvt-ios` will just process the data without storing results on disk.

Through the `--iocs` argument you can specify a [STIX2](https://oasis-open.github.io/cti-documentation/stix/intro) file defining a list of malicious indicators to check against the records extracted from the backup by mvt. Any matches will be highlighted in the terminal output as well as saved in the output folder using a "*_detected*" suffix to the JSON file name.
