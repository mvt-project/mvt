# Development

The Mobile Verification Toolkit team welcomes contributions of new forensic modules or other contributions which help improve the software.

## Testing

MVT uses `pytest` for unit and integration tests. Code style consistency is maintained with `flake8`, `ruff` and `black`. All can
be run automatically with:

```bash
make check
```

Run these tests before making new commits or opening pull requests.

## Profiling

Some MVT modules extract and process significant amounts of data during the analysis process or while checking results against known indicators. Care must be
take to avoid inefficient code paths as we add new modules.

MVT modules can be profiled with Python built-in `cProfile` by setting the `MVT_PROFILE` environment variable.

```bash
MVT_PROFILE=1 dev/mvt-ios check-backup test_backup
```

Open an issue or PR if you are encountering significant performance issues when analyzing a device with MVT.