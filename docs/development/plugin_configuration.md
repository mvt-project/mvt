# Plugin Configuration

Plugin packages that add [custom CLI commands](custom_commands.md) or
[modules](index.md#installed-module-packages) often need to store their
own settings, such as an API key, a cache folder or the timestamp of the last
synchronization. MVT provides a namespaced settings base class so each plugin
keeps its configuration in its own file.

!!! warning

    Do not write plugin settings to MVT's own `config.yaml`. MVT rewrites that
    file with the settings it knows about every time it starts, so any other
    section is deleted.

## Where Settings Are Stored

Each plugin gets one YAML file in a `plugins` folder next to MVT's own
configuration:

```
~/.config/mvt/plugins/<plugin name>.yaml
```

The exact parent folder follows the platform convention used for MVT's
`config.yaml` (for example `~/Library/Application Support/mvt` on macOS). Use
`mvt.common.plugin_config.plugin_config_path()` instead of building the path by
hand.

Plugin names must be lowercase and may only contain letters, digits and dashes,
matching the `mvt-plugin-<name>` package naming convention. MVT creates the
`plugins` folder with `0700` permissions and writes the settings files with
`0600` permissions, because they commonly hold credentials. Files are written
through a temporary file and moved into place, so an interrupted save never
leaves a partially written settings file behind.

## Defining Plugin Settings

Subclass `MVTPluginSettings`, set `plugin_name` and declare typed fields with
defaults:

```python
from typing import Optional

from mvt.common.plugin_config import MVTPluginSettings


class ExamplePluginSettings(MVTPluginSettings):
    plugin_name = "example-plugin"

    API_KEY: Optional[str] = None
    CACHE_FOLDER: str = "~/.cache/example-plugin"
    LAST_SYNC: Optional[str] = None
```

`load()` returns the current settings and `save()` writes them back:

```python
from datetime import datetime, timezone

import click


def sync():
    settings = ExamplePluginSettings.load()
    if not settings.API_KEY:
        raise click.ClickException(
            "No API key configured. Set MVT_PLUGIN_EXAMPLE_PLUGIN_API_KEY or "
            "run 'example-plugin configure'."
        )

    settings.LAST_SYNC = datetime.now(timezone.utc).isoformat()
    settings.save()
```

A missing settings file is not an error: the plugin then runs on the field
defaults and on whatever the environment provides. `save()` only persists the
values that differ from the defaults, and it never touches MVT's `config.yaml`.
A settings file that cannot be parsed, or that does not hold a mapping of
setting names to values, raises a `PluginConfigLoadError` naming the file.

Every subclass that sets its own `plugin_name` gets its own file and its own
environment namespace. A subclass that does not redefine `plugin_name` inherits
it, and therefore shares the file and the environment variables of its parent
class.

## Environment Variables

Every field can also be set with an environment variable. The prefix is
`MVT_PLUGIN_`, followed by the plugin name upper-cased with dashes replaced by
underscores, followed by the field name. For the example above:

```bash
export MVT_PLUGIN_EXAMPLE_PLUGIN_API_KEY=...
export MVT_PLUGIN_EXAMPLE_PLUGIN_CACHE_FOLDER=/tmp/example-cache
```

Settings resolve in this order, from highest to lowest priority:

1. Arguments passed to the settings class directly, such as
   `ExamplePluginSettings(API_KEY="...")`
2. Environment variables
3. The plugin's YAML file
4. The field defaults declared on the settings class

!!! tip

    On shared or multi-user machines, prefer passing API keys through
    environment variables rather than saving them to the plugin file. `save()`
    skips every value that the environment currently supplies, so a credential
    provided that way is not copied into the settings file when a plugin saves
    an unrelated setting.

Unknown keys in a plugin's YAML file are ignored, so a settings file written by
a newer version of a plugin does not break an older one.
