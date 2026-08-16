# Custom CLI Commands

MVT can load additional top-level commands into `mvt-ios` and `mvt-android`.
Custom commands are different from [custom forensic modules](development.md#custom-modules):
commands add new CLI operations, while modules add analysis steps to existing
`check-*` commands.

!!! warning

    Custom commands run as trusted Python code inside the MVT process. Install
    or load commands only from sources you trust. MVT does not sandbox
    third-party commands, and the MVT maintainers do not maintain them.

## Install a Command Package

Python packages can register a Click command or group for either MVT CLI. A
minimal package can expose this command from `my_mvt_plugin.py`:

```python
import click


@click.command()
@click.argument("path", type=click.Path(exists=True))
def summarize(path):
    """Summarize an acquisition."""
    click.echo(f"Summarizing {path}")
```

Register the object in the package's `pyproject.toml`. The entry-point name is
the command users invoke:

```toml
[project.entry-points."mvt.ios.cli_plugins"]
summarize = "my_mvt_plugin:summarize"

[project.entry-points."mvt.android.cli_plugins"]
summarize = "my_mvt_plugin:summarize"
```

Use only the iOS or Android group if the command is platform-specific. After
installing the package in the same environment as MVT, it appears directly in
the appropriate CLI:

```bash
mvt-ios summarize ./ios-backup
mvt-android summarize ./androidqf-output
```

For a `pipx` installation of MVT, inject the plugin into MVT's environment:

```bash
pipx inject mvt my-mvt-plugin
```

When MVT is installed in an active virtual environment, install the plugin with
`pip` in that environment.

## Load a Command File

For local commands that are not packaged, create a Python file that exports one
Click command or group named `cli`:

```python
import click


@click.command("case-summary")
@click.argument("path", type=click.Path(exists=True))
def cli(path):
    """Summarize a case directory."""
    click.echo(f"Summarizing {path}")
```

Pass the file before the custom command name:

```bash
mvt-ios --load-command ./case_summary.py case-summary ./ios-backup
```

`--load-command` can be repeated and also accepts a folder. MVT loads
non-hidden top-level `*.py` files in sorted order and skips `__init__.py`.
Every loaded file must export one `cli` object.

To load a file or folder on every invocation, set the platform-specific
environment variable:

```bash
export MVT_IOS_CUSTOM_COMMANDS=./ios_commands
export MVT_ANDROID_CUSTOM_COMMANDS=./android_commands
```

## Naming and Errors

Built-in MVT commands cannot be replaced. External command names must also be
unique; when installed packages or environment paths collide, MVT keeps the
first command and logs a warning. A collision from an explicit
`--load-command` is a usage error.

A package entry point or environment command that cannot be imported appears
as a marked broken command without preventing other MVT commands from working.
Invoke that command to see its package or file source and the underlying error.
An invalid command supplied explicitly with `--load-command` fails immediately
with a usage error.

Installed command packages use the entry-point name as the CLI command name.
The entry point must resolve to a `click.Command` or `click.Group`.
