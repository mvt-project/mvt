# Custom CLI Commands

MVT can load additional top-level commands into `mvt`, `mvt-ios` and
`mvt-android`. A command package chooses which of the three each of its
commands is added to.
Custom commands are different from [custom forensic modules](index.md#custom-modules):
commands add new CLI operations, while modules add analysis steps to existing
`check-*` commands.

!!! warning

    Custom commands run as trusted Python code inside the MVT process. Install
    or load commands only from sources you trust. MVT does not sandbox
    third-party commands, and the MVT maintainers do not maintain them.

## Install a Command Package

Python packages can register a Click command or group on one or more of the MVT CLIs.
A minimal package can expose this command from `my_mvt_plugin.py`:

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

Each entry-point group adds the command to one CLI: `mvt.ios.cli_plugins` to
`mvt-ios`, `mvt.android.cli_plugins` to `mvt-android` and `mvt.cli_plugins` to
`mvt`. Register the command in the group of every CLI which should offer it: a
platform-specific command belongs in one platform group, and a command which
handles acquisitions of both platforms, as above, in both. After installing the
package in the same environment as MVT, the command appears directly in those
CLIs:

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

Command packages that need their own settings, such as an API key, should store
them in a namespaced [plugin configuration file](plugin_configuration.md)
rather than in MVT's own `config.yaml`.

### Commands on `mvt`

The `mvt` command hosts what belongs to neither platform: `version`,
`completion` and `download-iocs`. A plugin command which is not about the
acquisition of one platform, such as one which configures the plugin or
synchronizes the indicators it uses, belongs there too, in the
`mvt.cli_plugins` group:

```toml
[project.entry-points."mvt.cli_plugins"]
my-plugin = "my_mvt_plugin:my_plugin"
```

Commands in this group are added to `mvt` only, so this one is invoked as
`mvt my-plugin`. A command on `mvt` has nothing but its name to say which
plugin it belongs to, so name it after the plugin, and make it a Click group
when the plugin has several operations to offer, such as
`mvt my-plugin configure`.

## Developing a Command Locally

A package is how a command is distributed. While a command is being written,
MVT can load it straight from its file instead, so the package need not be
reinstalled after every change; an editable install of the package does the
same through its entry points. Create a Python file that exports one Click
command or group named `cli`:

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

To load a file or folder on every invocation, set the environment variable of
the CLI the commands belong on. Like the entry-point groups, each variable adds
its commands to one CLI only:

```bash
export MVT_CUSTOM_COMMANDS=./commands
export MVT_IOS_CUSTOM_COMMANDS=./ios_commands
export MVT_ANDROID_CUSTOM_COMMANDS=./android_commands
```

## Naming and Errors

Built-in MVT commands cannot be replaced. External command names must also be
unique on each CLI; when installed packages or environment paths collide, MVT
keeps the first command and logs a warning. The environment path of a CLI is
registered before its installed packages, so a command loaded from there wins a
collision with a package. A collision from an explicit `--load-command` is a
usage error.

A package entry point or environment command that cannot be imported appears
as a marked broken command without preventing other MVT commands from working.
Invoke that command to see its package or file source and the underlying error.
An invalid command supplied explicitly with `--load-command` fails immediately
with a usage error.

Installed command packages use the entry-point name as the CLI command name.
The entry point must resolve to a `click.Command` or `click.Group`.
