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

## Parallel module execution

Extraction modules run concurrently, using four worker threads by default. Use
`--jobs INTEGER` to change the worker limit, or `--jobs 1` for sequential
execution and live per-line logging:

```bash
mvt-ios check-backup --jobs 8 --output ./out ./backup
```

The scheduler starts a module only after all of its declared dependencies have
completed. Results, alerts, and timeline entries are still aggregated in stable
topological order. During parallel execution, console records from each module
are buffered and printed together as a labeled block when that module finishes;
`command.log` is written immediately and retains the complete log stream.

Parallel-safe modules must log through `self.log`, must not write directly to
stdout or stderr, and must not mutate shared global state. A module that uses a
non-thread-safe resource or direct terminal output can opt out:

```python
class TerminalModule(MVTModule):
    parallel_safe = False
```

Such modules run synchronously and exclusively after active workers finish.

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

Custom modules are considered parallel-safe by default. Follow the parallel
module requirements above or set `parallel_safe = False`.

Use `supported_commands` to restrict a module to specific platform/command
pairs. Missing or empty `supported_commands` means the module is available to
all commands, which keeps older modules compatible. Supported pairs are:

```python
("ios", "check-backup")
("ios", "check-fs")
("ios", "check-iocs")
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

## Profiling

Some MVT modules extract and process significant amounts of data during the analysis process or while checking results against known indicators. Care must be
take to avoid inefficient code paths as we add new modules.

MVT modules can be profiled with Python built-in `cProfile` by setting the
`MVT_PROFILE` environment variable. Profiling forces sequential execution even
when `--jobs` is greater than one.

```bash
MVT_PROFILE=1 dev/mvt-ios check-backup test_backup
```

Open an issue or PR if you are encountering significant performance issues when analyzing a device with MVT.
