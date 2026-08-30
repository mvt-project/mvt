# Check an iOS Sysdiagnose

`mvt-ios check-sysdiagnose` prepares an iOS sysdiagnose archive for analysis by
custom MVT modules. MVT does not include built-in sysdiagnose modules. The
command runs the modules of the installed
[plugin packages](../development/index.md#installed-module-packages) which
declare support for it. Install at least one such package first.

The command accepts either an extracted sysdiagnose directory or the original
gzip-compressed tar archive.

```bash
mvt-ios check-sysdiagnose --output ./results \
    ./sysdiagnose_2024.01.02_03-04-05+0200.tar.gz
```

Use `--hashes` to include hashes for analyzed files in `info.json`, and
`--list-modules` to display the eligible modules without running them.

## Writing a custom module

Extend `SysdiagnoseExtraction` from `mvt.plugin`, see
[Writing a module](../development/index.md#writing-a-module). The module reads
the archive the same way whether MVT was given a folder or a tar archive. It
declares the command in `supported_commands`. While writing one,
[load it from its file](../development/index.md#developing-modules-locally).

```python
from mvt.plugin import SysdiagnoseExtraction


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

MVT extracts a tar archive first. It calls `from_sysdiagnose_folder()` on each
module before `run()`. `ips_files` lists the IPS crash reports.

`_get_files_by_pattern()` and `_get_file_content()` are internal helpers of the
base class. Use them to read the archive. Their names and signatures can change
between releases. See `src/mvt/ios/modules/sysdiagnose/base.py`.
