# Check a Filesystem Dump with `mvt-ios`

When you are ready, you can proceed running `mvt-ios` against the filesystemp dump or mount point:

    $ mvt-ios check-fs --help
    Usage: mvt-ios check-fs [OPTIONS] DUMP_PATH

      Extract artifacts from a full filesystem dump

    Options:
      -i, --iocs PATH     Path to indicators file
      -o, --output PATH   Specify a path to a folder where you want to store JSON
                          results

      -f, --fast          Avoid running time/resource consuming features
      -l, --list-modules  Print list of available modules and exit
      -m, --module TEXT   Name of a single module you would like to run instead of
                          all

      --help              Show this message and exit.

Following is an example of basic usage of `check-fs`:

```bash
mvt-ios check-fs /path/to/filesystem/dump/ --output /path/to/output/
```

This command will create a few JSON files containing the results from the extraction. If you do not specify a `--output` option, `mvt-ios` will just process the data without storing results on disk.

Through the `--iocs` argument you can specify a [STIX2](https://oasis-open.github.io/cti-documentation/stix/intro) file defining a list of malicious indicators to check against the records extracted from the backup by mvt. Any matches will be highlighted in the terminal output as well as saved in the output folder using a "*_detected*" suffix to the JSON file name.
