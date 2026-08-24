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

Selecting a single module also runs its transitive dependencies. If a dependency
is unavailable or the dependency graph contains a cycle, the command logs a
warning and does not run any modules.

## Custom modules

Module-running `check-*` commands can load custom modules from Python files that
are not installed as part of MVT. Load one file with:

```bash
mvt-ios check-backup --load-module ./example_module.py --output ./out ./backup
```

You can also load a folder. MVT loads non-hidden top-level `*.py` files in
sorted order and skips `__init__.py`:

```bash
mvt-ios check-fs --load-module ./custom_modules ./filesystem-dump
```

Set `MVT_CUSTOM_MODULES` to load a folder for every module-running command. This
folder is loaded before any `--load-module` path:

```bash
MVT_CUSTOM_MODULES=./custom_modules mvt-android check-bugreport ./bugreport.zip
```

Custom modules are normal `MVTModule` subclasses:

```python
from mvt.common.module import MVTModule


class ExampleCustomModule(MVTModule):
    supported_commands = (("ios", "check-backup"), ("ios", "check-fs"))
    slug = "example_custom_module"

    def run(self):
        self.results = [{"message": "custom module ran"}]

    def check_indicators(self):
        pass

    def serialize(self, result):
        return None
```

Use `supported_commands` to declare the platform/command pairs a module
supports. Empty `supported_commands` means the module will not run and MVT logs
a warning. This explicit declaration is required for every command. Supported
pairs are:

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

Custom modules can depend on existing MVT module classes. Dependencies are
resolved with the same ordering logic as built-in modules, and custom modules
are appended after built-ins before ordering:

```python
from mvt.common.module import MVTModule
from mvt.ios.modules.backup.manifest import Manifest


class DependentCustomModule(MVTModule):
    supported_commands = (("ios", "check-backup"),)
    dependencies = (Manifest,)

    def run(self):
        manifest_results = self.get_dependency_results(Manifest)
        self.results = [{"manifest_entries": len(manifest_results)}]
```

## Installed module packages

Python packages can register modules so they load automatically in every
module-running `check-*` command, without `--load-module` or
`MVT_CUSTOM_MODULES`. Register an entry point in the `mvt.modules` group in
the package's `pyproject.toml`:

```toml
[project.entry-points."mvt.modules"]
mvt-plugin-amnesty-custom = "mvt_plugin_amnesty_custom:get_modules"
```

The entry point must resolve to an iterable of `MVTModule` subclasses, or to
a callable returning one:

```python
from mvt.common.module import MVTModule


class PackagedModule(MVTModule):
    supported_commands = (("ios", "check-backup"),)

    def run(self):
        self.results = [{"message": "packaged module ran"}]


def get_modules() -> list[type[MVTModule]]:
    return [PackagedModule]
```

Installed modules follow the same rules as other custom modules: each module
must declare `supported_commands`, and dependencies are resolved with the
standard ordering logic. A broken entry point is skipped with a warning and
does not prevent MVT from running. As with custom commands, installed module
packages run as trusted code inside the MVT process, so install only packages
from sources you trust.

For a `pipx` installation of MVT, inject the package into MVT's environment:

```bash
pipx inject mvt mvt-plugin-amnesty-custom
```

### Naming module packages

Name module packages `mvt-plugin-<name>` (import package `mvt_plugin_<name>`),
and include the name of the publishing organization or author so packages from
different groups do not collide: for example, Amnesty International's custom
modules would be distributed as `mvt-plugin-amnesty-custom` with the import
package `mvt_plugin_amnesty_custom`.

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
  prefix stripped: modules in `mvt_plugin_amnesty_custom` log as
  `mvt.ext.amnesty_custom.*`.
- Files loaded with `--load-module` or `MVT_CUSTOM_MODULES` log as
  `mvt.ext.<file name>`.

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

## Profiling

Some MVT modules extract and process significant amounts of data during the analysis process or while checking results against known indicators. Care must be
take to avoid inefficient code paths as we add new modules.

MVT modules can be profiled with Python built-in `cProfile` by setting the `MVT_PROFILE` environment variable.

```bash
MVT_PROFILE=1 dev/mvt-ios check-backup test_backup
```

Open an issue or PR if you are encountering significant performance issues when analyzing a device with MVT.
