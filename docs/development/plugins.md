# Managing Plugins

Plugin packages extend MVT with additional
[forensic modules](index.md#custom-modules) and
[CLI commands](custom_commands.md). Because installed packages load
automatically, `mvt plugins` audits what is installed and checks whether
updates are available. The command lives on `mvt` only, although the packages
it lists extend `mvt-ios` and `mvt-android` too.

## List Installed Plugins

```bash
mvt plugins list
```

```
                        Installed MVT plugins
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━┓
┃ Name                ┃ Version ┃ Origin       ┃ Modules ┃ Commands  ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━┩
│ mvt-plugin-example  │ 1.2.0   │ pypi         │       4 │ summarize │
│ mvt-plugin-research │ 0.1.0   │ git+3f9a1c7d │       2 │ -         │
│ mvt-plugin-local    │ 0.0.1   │ local        │       1 │ triage    │
└─────────────────────┴─────────┴──────────────┴─────────┴───────────┘
```

The origin records where each package was installed from: `pypi` for a package
installed from a package index, `git+<commit>` for a package installed directly
from a repository, and `local` for a package installed from a local folder or
archive rather than from an index, including an editable development install.
The last two columns show how many forensic modules the package contributes and
which CLI commands it adds.

A plugin whose modules cannot be imported is listed with `error` in the
`Modules` column rather than breaking the listing.

## Check for Updates

```bash
mvt plugins check-updates
```

```
Plugin updates available:
  mvt-plugin-example  1.2.0 → 1.3.0
    Upgrade with: pip install -U mvt-plugin-example

MVT does not install plugin updates. Run the command above when you decide to
upgrade.
```

Packages installed from a package index are compared against the latest release
published for them. A package which was never published, for example a plugin
distributed only within an organization, is skipped silently.

!!! note

    Packages shown with the `pypi` origin are compared against
    [PyPI](https://pypi.org), whichever index they were installed from. A
    plugin installed from a private index under a name which also exists on
    PyPI is therefore compared against the unrelated public package of that
    name. Give plugins published to a private index a name which is not taken
    on PyPI, and treat an unexpected update suggestion as a reason to check
    where the package would come from.

!!! warning

    MVT never installs or upgrades a plugin itself, it only prints the command
    which does. Upgrading a plugin in the middle of an investigation changes
    the modules producing the results, and a plugin runs as trusted code inside
    the MVT process, so pulling in a new version is a decision for the analyst
    to make deliberately and not a side effect of running a check.

## Automatic Update Checks

MVT also reports available plugin updates in the banner printed when a command
starts:

```
        MVT - Mobile Verification Toolkit

        https://mvt.re
        Version: 2026.7.29

        Plugin updates available:
          mvt-plugin-example  1.2.0 → 1.3.0   (pip install -U mvt-plugin-example)
```

This check runs at most once every 12 hours. In between checks MVT prints the
findings of the latest check without contacting anything, so a plugin update
stays visible without a lookup on every command. The
`mvt plugins check-updates` command checks immediately, regardless of when the
last check happened.

The automatic check is skipped when the `--disable-update-check` option is
used, when `NETWORK_ACCESS_ALLOWED` is disabled in the MVT configuration, and
when no plugins are installed.

## Plugins Installed From a Repository

A plugin installed with `pip install "mvt-plugin-example @ git+<url>"` is
checked by asking the remote repository which commit the installed revision
points at now. MVT runs git and ssh in batch mode, so a repository which needs
credentials MVT does not already have fails the check instead of prompting for
them. The check is skipped silently when git is not available, when the
repository cannot be reached, and when access to it is denied.

How the plugin was installed decides what an update means:

- A plugin installed from a branch is reported as outdated when the branch has
  moved past the installed commit.
- A plugin installed from a specific commit or a tag is pinned. It is never
  reported as outdated, however far the branch it came from moves on.

Pinning a plugin to a commit or a tag is therefore the way to keep the modules
used across an investigation stable.
