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

## Profiling

Some MVT modules extract and process significant amounts of data during the analysis process or while checking results against known indicators. Care must be
take to avoid inefficient code paths as we add new modules.

MVT modules can be profiled with Python built-in `cProfile` by setting the `MVT_PROFILE` environment variable.

```bash
MVT_PROFILE=1 dev/mvt-ios check-backup test_backup
```

Open an issue or PR if you are encountering significant performance issues when analyzing a device with MVT.
