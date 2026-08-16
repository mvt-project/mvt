# Check an iOS Sysdiagnose

`mvt-ios check-sysdiagnose` prepares an iOS sysdiagnose archive for analysis by
custom MVT modules. MVT does not include built-in sysdiagnose modules. You must
load at least one custom module that explicitly supports this command.

The command accepts either an extracted sysdiagnose directory or the original
gzip-compressed tar archive.

```bash
mvt-ios check-sysdiagnose \
    --load-module ./sysdiagnose_modules.py \
    --output ./results \
    ./sysdiagnose_2024.01.02_03-04-05+0200.tar.gz
```

Use `--hashes` to include hashes for analyzed files in `info.json`, and
`--list-modules` to display the eligible custom modules without running them.

## Writing a custom module

Extend `SysdiagnoseExtraction` to access the archive contents consistently for
both directory and tar inputs. Each module must declare the command explicitly
in `supported_commands`.

```python
from mvt.ios.modules.sysdiagnose import SysdiagnoseExtraction


class ExampleSysdiagnoseModule(SysdiagnoseExtraction):
    supported_commands = (("ios", "check-sysdiagnose"),)
    slug = "example_sysdiagnose"

    def run(self):
        paths = self._get_files_by_pattern("*/example.log")
        if paths:
            content = self._get_file_content(paths[0]).decode("utf-8", "replace")
            self.results = [{"content": content}]

    def check_indicators(self):
        pass

    def serialize(self, result):
        return None
```

The base class provides `from_sysdiagnose_folder()` and
`from_sysdiagnose_tar()` setup hooks, as well as protected file lookup, file
reading, and timezone extraction helpers. IPS crash-report metadata is exposed
on `ips_files`.
