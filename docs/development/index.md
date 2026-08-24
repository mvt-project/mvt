# Development

The Mobile Verification Toolkit team welcomes contributions of new forensic modules or other contributions which help improve the software.

## Local environment

MVT uses `uv` for dependency management. To install the project and development dependencies from the locked environment, run:

```bash
make install
```

## Testing

MVT uses `pytest` for unit and integration tests. Code style consistency is maintained with `ruff` and `mypy`. All can
be run automatically with:

```bash
make check
```

Run these tests before making new commits or opening pull requests.

## Module dependencies

Modules can require other modules to run first by declaring their classes in
`dependencies`. The command runner uses a stable topological ordering, so the
existing module list order is preserved wherever dependency constraints allow.

```python
class DependentModule(MVTModule):
    dependencies = (PrerequisiteModule,)

    def run(self):
        prerequisite_results = self.get_dependency_results(PrerequisiteModule)
```

Selecting a single module also runs its transitive dependencies.

A module can only depend on modules the command it runs in also has. When a
declared dependency is not among them, the command logs a warning naming the
module and the missing dependency, skips that module and everything depending
on it, and runs the rest of the analysis. Selecting such a module with
`--module` therefore leaves nothing to run, which the warning explains.

A cycle in the dependency graph is a programming error rather than a
configuration problem: the command logs a warning and runs no modules at all.

## Custom modules

MVT's module-running `check-*` commands can run forensic modules which are not
part of MVT. Custom modules are distributed as plugin packages. A Python
package installed next to MVT registers its modules through an entry point.
The modules then load automatically in every command they support, see
[Installed module packages](#installed-module-packages). `mvt plugins list`
shows the installed packages and where each one was installed from.

MVT can also load module files by path, with `--load-module` and
`MVT_CUSTOM_MODULES`, see
[Developing modules locally](#developing-modules-locally). This can be used
while writing a module. Use a Python package to distribute one.

A custom module declares in `supported_commands` the platform and command
pairs it runs in. A module with empty `supported_commands` does not run and
MVT logs a warning. The nine pairs are:

```python
("ios", "check-backup")
("ios", "check-fs")
("ios", "check-iocs")
("ios", "check-sysdiagnose")
("android", "check-backup")
("android", "check-bugreport")
("android", "check-androidqf")
("android", "check-intrusion-logs")
("android", "check-iocs")
```

`check-iocs` re-checks stored results rather than an acquisition. It matches
every `<slug>.json` file in the results folder to the module with that slug.
It then runs that module's `check_indicators()` again.

### Writing a module

A module subclasses `MVTModule` or one of the base classes below and
implements `run()`. `check_indicators()` and `serialize()` are optional. The
first matches results against IOCs or detections. The second returns timeline
records.

```python
from mvt.plugin import IOSExtraction, convert_unix_to_iso


class ExampleCustomModule(IOSExtraction):
    supported_commands = (
        ("ios", "check-backup"),
        ("ios", "check-fs"),
    )
    slug = "example_custom_module"

    def run(self):
        self.results = [{"checked_at": convert_unix_to_iso(0)}]

    def check_indicators(self):
        pass

    def serialize(self, result):
        return None
```

The base classes are:

- `MVTModule`: the base of every module. It provides `self.results`,
  `self.alertstore`, `self.log`, `self.indicators` and
  `get_dependency_results()`. Subclass it directly for a module which reads
  only the results of other modules.
- `IOSExtraction`: `("ios", "check-backup")` and `("ios", "check-fs")`. Adds
  `_find_ios_database()`, which locates a module's database in a backup or in
  a filesystem dump and repairs it if it is malformed. Adds
  `_get_backup_files_from_manifest()`, `_get_backup_file_from_id()` and
  `_get_fs_files_from_patterns()`. Adds `_open_sqlite_db()`, which opens a
  database read-only.
- `SysdiagnoseExtraction`: `("ios", "check-sysdiagnose")`. MVT extracts the
  archive and calls `from_sysdiagnose_folder()` before `run()`. The module
  reads files with `_get_files_by_pattern()` and `_get_file_content()`.
  `ips_files` lists the crash reports. See
  [Check an iOS Sysdiagnose](../ios/sysdiagnose.md).
- `AndroidQFModule`: `("android", "check-androidqf")`. MVT calls `from_dir()`
  or `from_zip()` with the file list of the acquisition. The module reads
  files with `_get_files_by_pattern()` and `_get_file_content()`.
  `_get_device_timezone()` returns the device timezone.
- `AndroidBackupModule`: `("android", "check-backup")`. MVT calls `from_dir()`
  or `from_ab()`. The module reads files with `_get_files_by_pattern()` and
  `_get_file_content()`.
- `BugReportModule`: `("android", "check-bugreport")`. MVT calls `from_dir()`
  or `from_zip()`. The module reads files with `_get_files_by_pattern()`,
  `_get_files_by_patterns()` and `_get_file_content()`.
  `_get_dumpstate_file()` returns the dumpstate file, and
  `_get_file_modification_time()` the modification time of a file.

The underscore-named helpers are internal to the base classes. Plugin modules
can call them. Their names and signatures can change between releases. Read
the base class in `src/mvt/ios/modules` or `src/mvt/android/modules` before
relying on one.

### Depending on a built-in module

A module which post-processes records generated by one or more built-in MVT
modules must declare the source modules in `dependencies`. It reads their
results with `get_dependency_results()`. Import the class from its family
package: `mvt.ios.modules.backup`, `mvt.ios.modules.fs`,
`mvt.ios.modules.mixed`, `mvt.android.modules.androidqf`,
`mvt.android.modules.backup`, `mvt.android.modules.bugreport` or
`mvt.android.modules.intrusion_logs`.

```python
from mvt.ios.modules.backup import Manifest
from mvt.plugin import MVTModule


class DependentCustomModule(MVTModule):
    supported_commands = (("ios", "check-backup"),)
    dependencies = (Manifest,)

    def run(self):
        manifest_results = self.get_dependency_results(Manifest)
        self.results = [{"manifest_entries": len(manifest_results)}]
```

Dependencies are ordered as for the built-in modules, with custom modules
appended after the built-ins, see [Module dependencies](#module-dependencies).
A dependency has to run in every command the module supports. Where it does
not, MVT skips the module with a warning.

`get_dependency_results()` returns the plain dictionaries the module produced.
They are the same records it writes to `<slug>.json`. Typed results per module
are planned.

### Replacing a built-in module

A custom module which extends a built-in one runs alongside it, and when the
two share a slug they write to the same results file. MVT warns about that
collision, naming both modules, where each came from and the file the later one
overwrites, but it runs them both. Set `replaces` to the class the module
supersedes to take that module's place instead: when both are available to a
command, the named module is dropped from the run.

```python
from mvt.ios.modules.backup import Manifest as BuiltinManifest


class Manifest(BuiltinManifest):
    supported_commands = (("ios", "check-backup"),)
    replaces = BuiltinManifest
```

Keeping the class name of the replaced module, as above, keeps the name
`--module` selects the module by and the slug its results file is named after.
A replacement with a different class name writes to a file named after its own
slug, unless it sets `slug` to the slug of the module it replaces, and
`--module` still selects it by the name of the replaced module, which MVT logs.
Taking over the slug of a replaced module is not a collision and is not warned
about, because that module is no longer part of the run.

Modules which depend on the replaced module receive the replacement instead, so
`get_dependency_results(BuiltinManifest)` returns the replacement's results. A
module must not depend on the module it replaces: that module does not run, so
the replacement has to produce the data itself, and MVT logs a warning when a
module declares both.

A replacement takes on the obligations of the module it replaces. If it
declares a dependency the command does not provide, it is skipped like any
other module with an unavailable dependency, and the module it replaced stays
out of the run: neither of them produces results, and the modules depending on
the replaced module are skipped as well.

Subclassing the replaced module is not required, but a replacement which is not
a subclass is logged with a warning, because its results may not be what the
modules depending on the replaced module expect. Naming a module the command
does not run has no effect, and modules which replace each other in a cycle all
keep running and replace nothing. Every applied substitution is logged, so it
is recorded in `command.log` when the command runs with an `--output` folder.

Every command resolves replacements on its own. `check-iocs` matches stored
results files against the slugs of the modules available for that command, so a
replacement checks the indicators of its own results only if it also declares
the `("ios", "check-iocs")` pair; otherwise the built-in module it replaced
re-checks the file. It also matches `--module` on the class name only, so pass
a differently named replacement's own name there, not the name of the module
it replaces.

### Importing from MVT

Import from `mvt.plugin` if it has what you need. The names it exports are
kept working on a best-effort basis. A change to one of them is announced in
the release notes. Anything else in `mvt` can be imported too, but may change
between releases without notice. The plugin interface is best effort.

`mvt.plugin` exports the base classes above and `Command`, `Alert` and
`AlertLevel`, the result types, `DatabaseNotFoundError` and
`DatabaseCorruptedError`, the timestamp converters, the settings API of
[Plugin Configuration](plugin_configuration.md), MVT's own `settings`,
`get_plugin_logger()` and `MVT_VERSION`. `src/mvt/plugin.py` holds the list.
Read MVT's `settings` for values such as `NETWORK_ACCESS_ALLOWED` and
`NETWORK_TIMEOUT`. Plugin values go in the plugin's own settings file.

## Installed module packages

Python packages can register modules so they load automatically in every
module-running `check-*` command, without `--load-module` or
`MVT_CUSTOM_MODULES`. Register an entry point in the `mvt.modules` group in
the package's `pyproject.toml`:

```toml
[project.entry-points."mvt.modules"]
mvt-plugin-example-org = "mvt_plugin_example_org:get_modules"
```

The entry point must resolve to an iterable of `MVTModule` subclasses, or to
a callable returning one:

```python
from mvt.plugin import MVTModule


class PackagedModule(MVTModule):
    supported_commands = (("ios", "check-backup"),)

    def run(self):
        self.results = [{"message": "packaged module ran"}]


def get_modules() -> list[type[MVTModule]]:
    return [PackagedModule]
```

`get_modules()` is the package's module list, written by hand. A package which
keeps its modules in separate files imports each class there and lists it. A
module missing from the list does not load.

Installed modules follow the same rules as other custom modules: each module
must declare `supported_commands`, and dependencies are resolved with the
standard ordering logic. A broken entry point is skipped with a warning and
does not prevent MVT from running. As with custom commands, installed module
packages run as trusted code inside the MVT process, so install only packages
from sources you trust.

For a `pipx` installation of MVT, inject the package into MVT's environment:

```bash
pipx inject mvt mvt-plugin-example-org
```

Module packages that need their own settings, such as an API key, should store
them in a namespaced [plugin configuration file](plugin_configuration.md)
rather than in MVT's own `config.yaml`.

### Naming module packages

Name module packages `mvt-plugin-<name>` (import package `mvt_plugin_<name>`),
and include the name of the publishing organization or author so packages from
different groups do not collide: for example, an organisation's custom modules
would be distributed as `mvt-plugin-example-org` with the import package
`mvt_plugin_example_org`.

The prefix makes module packages easy to find on PyPI and keeps their import
names from clashing with unrelated Python packages. It is a convention, not a
technical requirement: modules load through the `mvt.modules` entry point
regardless of what the package is called, and existing packages with other
names keep working. Note that the prefix is also not a mark of authenticity —
anyone can publish a package with any available name, so vet a module package
and its publisher before installing it, whatever it is called.

### Module logging

Modules log through `self.log`, and MVT names the logger for where the module
came from. MVT's own modules log under their dotted path (for example
`mvt.ios.modules.mixed.whatsapp`). Everything external is namespaced under
`mvt.ext` to keep it visually distinct from built-in modules and isolated from
MVT's internal logger tree:

- Installed packages log under `mvt.ext.<package>`, with the `mvt_plugin_`
  prefix stripped: modules in `mvt_plugin_example_org` log as
  `mvt.ext.example_org.*`.
- Files loaded with `--load-module` or `MVT_CUSTOM_MODULES` log as
  `mvt.ext.<file name>`.

Outside a module class, for example in a custom command line handler, log
through `get_plugin_logger(__name__)`. It returns a logger in the same
namespace.

## Developing modules locally

While a module is being written, load it from its file. `--load-module` takes a
Python file, or a folder of them, on every module-running command, and can be
repeated:

```bash
mvt-ios check-backup --load-module ./example_module.py --output ./out ./backup
```

For a folder, MVT loads its non-hidden top-level `*.py` files in sorted order
and skips `__init__.py`. `MVT_CUSTOM_MODULES` names a folder to load on every
module-running command, before any `--load-module` path:

```bash
MVT_CUSTOM_MODULES=./custom_modules mvt-android check-bugreport ./bugreport.zip
```

Files loaded this way follow the same rules as packaged modules.
`--list-modules` reports them with the SHA-256 hash of the file in place of a
version. An editable install of the package (`pip install -e .`) also works:
the modules load through the entry point, and `mvt plugins list` shows the
package with the `local` origin.

Loading by path is for development. Move a module into a package once it
works.

## Auditing loaded modules

Because installed module packages load automatically, MVT records where every
module came from:

- `--list-modules` groups the available modules by source: MVT itself
  (with its version), each installed package (with its version and, when
  installed directly from a repository, the commit), and each file loaded
  with `--load-module` or `MVT_CUSTOM_MODULES` (with the SHA-256 hash of the
  file).
- When a command runs with an `--output` folder, the `command.log` file
  records one line per module source with the source's version or hash and
  the list of modules loaded from it.
- `mvt plugins list` lists the installed packages, where each of them
  was installed from and how many modules it contributes, see
  [Managing Plugins](plugins.md).

## Profiling

Some MVT modules extract and process significant amounts of data during the analysis process or while checking results against known indicators. Care must be
take to avoid inefficient code paths as we add new modules.

MVT modules can be profiled with Python built-in `cProfile` by setting the `MVT_PROFILE` environment variable.

```bash
MVT_PROFILE=1 dev/mvt-ios check-backup test_backup
```

Open an issue or PR if you are encountering significant performance issues when analyzing a device with MVT.
