# MVT for macOS (GUI)

A native SwiftUI app that wraps the `mvt-ios`, `mvt-android` and `mvt`
command-line tools from this repository. It does not reimplement any
analysis. It builds the same command lines you would type, runs them, and
shows the output and results.

## Requirements

- macOS 13 Ventura or later
- Xcode 15 or later
- Python 3.10 or later, used to run MVT (`brew install python`). The Python
  that ships with the Xcode command line tools is 3.9, which is too old.

## Build and run

1. Open `macos/MVTGUI.xcodeproj` in Xcode.
2. Select the **MVTGUI** scheme and **My Mac**, then press **⌘R**.

The project signs with "Sign to Run Locally", so you don't need a developer
team to run it on your own Mac. To share the app with other people, pick your
team under *Signing & Capabilities* and archive it (**Product ▸ Archive**).

From the command line:

```bash
xcodebuild -project macos/MVTGUI.xcodeproj -scheme MVTGUI \
  -configuration Release -derivedDataPath macos/build build
open macos/build/Build/Products/Release/MVTGUI.app
```

The `macOS GUI` GitHub Actions workflow runs the same build and uploads the
zipped `.app` as an artifact.

## First launch

The **Setup** screen looks for MVT in these places:

1. the folder set in **Settings** (⌘,)
2. the app's own virtualenv (`~/Library/Application Support/MVT GUI/venv`)
3. `~/.local/bin` (pipx and `uv tool`), `/opt/homebrew/bin`, `/usr/local/bin`
4. your login shell's `PATH`

If MVT isn't found, click **Install MVT**. The app creates a private
virtualenv and installs MVT with pip, either the PyPI release or a local
source folder. Use **Local source folder** with this repository to run your
fork's code. With **Editable install** turned on, changes to `src/mvt` apply
without reinstalling.

Then open **Indicators ▸ Download Indicators** to fetch the public STIX2
indicators. Every check uses them automatically.

## What's in the app

| Sidebar item | Runs |
| --- | --- |
| iOS ▸ Check Backup | `mvt-ios check-backup` |
| iOS ▸ Check Filesystem Dump | `mvt-ios check-fs` |
| iOS ▸ Check Sysdiagnose | `mvt-ios check-sysdiagnose` |
| iOS ▸ Decrypt Backup | `mvt-ios decrypt-backup` |
| iOS ▸ Extract Backup Key | `mvt-ios extract-key` |
| iOS / Android ▸ Re-check Results | `mvt-ios check-iocs` / `mvt-android check-iocs` |
| Android ▸ Check AndroidQF | `mvt-android check-androidqf` |
| Android ▸ Check Backup (SMS) | `mvt-android check-backup` |
| Android ▸ Check Bug Report | `mvt-android check-bugreport` |
| Android ▸ Check Intrusion Logs | `mvt-android check-intrusion-logs` |
| Indicators ▸ Download Indicators | `mvt download-iocs` |
| Results | Reads `alerts.json`, `info.json` and the other files in a results folder |

Details:

- Each command's form offers the options that command accepts: STIX2
  indicator files, results folder, fast mode, hashing, running a single
  module (**List Modules** shows the names), timezone and VirusTotal lookups.
- Output streams into the console live. Alert lines are colored by severity
  and counted, and **Alerts only** hides everything else.
- **Results** shows alerts in a sortable, searchable table. Selecting an
  alert shows the record that triggered it and the matched indicator.
- The app passes backup passwords and the VirusTotal API key through
  `MVT_IOS_BACKUP_PASSWORD`, `MVT_ANDROID_BACKUP_PASSWORD` and
  `MVT_VT_API_KEY`. They never appear on the command line or in the process
  table. Android commands always get `--non-interactive`, because the GUI has
  no terminal to answer prompts.
- **Settings** has the MVT location, the update-check toggles and verbose
  output.

### How to acquire data

- **iOS:** make an encrypted backup in Finder, or with `idevicebackup2`
  from libimobiledevice. Decrypt it with **Decrypt Backup**. When that
  finishes, **Check Decrypted Backup** carries the decrypted folder over to
  **Check Backup**.
- **Android:** collect data with
  [AndroidQF](https://github.com/mvt-project/androidqf), then use
  **Check AndroidQF** on its output.

## Project layout

```
macos/
├── MVTGUI.xcodeproj
└── MVTGUI/
    ├── MVTGUIApp.swift          App entry point, window and Settings scenes
    ├── Models/
    │   ├── MVTCommand.swift     Every supported command and its options
    │   ├── CommandForm.swift    Form state → arguments + environment
    │   └── AppState.swift       Navigation and the shared runner
    ├── Services/
    │   ├── ProcessRunner.swift  Runs a process and streams its output
    │   ├── MVTEnvironment.swift Finds MVT/Python, preferences
    │   └── LogLine.swift        Alert-level parsing of MVT's log output
    └── Views/                   SwiftUI screens
```

To expose a new MVT command or option, add a case to `MVTCommand`, list its
flags in `options`, and map them to arguments in
`CommandForm.invocation()`.

The app runs without the App Sandbox because it must launch the MVT
executables and read acquisitions from anywhere on disk.

## Staying in sync with upstream MVT

This repository is a fork of
[mvt-project/mvt](https://github.com/mvt-project/mvt). Two workflows keep it
current:

- **Sync upstream** (`.github/workflows/sync-upstream.yml`) runs daily and
  merges new upstream commits into a `sync/upstream` branch. It then opens a
  pull request, or updates the open one, listing the new commits. The pull
  request flags upstream changes to files the GUI depends on (CLI
  definitions, log format, alerts, settings). Nothing lands on `main` until
  you merge that pull request. If upstream conflicts with the fork's changes,
  or the sync can't push, the run fails and opens an **Upstream sync needs
  attention** issue with instructions.
- **macOS GUI** (`.github/workflows/macos-gui.yml`) builds the app and runs
  `macos/scripts/check_cli_contract.py` on every change to `macos/`, `src/`
  or `pyproject.toml`, and on every sync branch. The contract check installs
  MVT from the checkout and verifies what the app relies on: the commands,
  flags, `MVT_*` environment variables, the `Version:` line, the
  `<LEVEL> ALERT` log prefixes, and the `alerts.json`/`info.json` format
  (by running a real check on the test backup). It warns when upstream adds
  a command the GUI doesn't offer yet.

One-time setup on GitHub:

1. Merge this work into `main`. Scheduled workflows only run from the
   default branch.
2. **Actions** tab: enable workflows. Forks have them disabled at first.
3. **Settings → Actions → General → Workflow permissions**: select *Read and
   write permissions* and tick *Allow GitHub Actions to create and approve
   pull requests*.
4. **Settings → General → Features**: enable **Issues** so conflict reports
   have somewhere to go. Failed runs also send you an email.
5. Recommended: add a `SYNC_TOKEN` repository secret. Use a fine-grained
   personal access token for this repository with *Contents*, *Pull
   requests* and *Workflows* read/write. Without it, the sync can't push
   upstream changes to `.github/workflows/`, and its pull requests don't
   trigger the Tests/Ruff checks (it still runs the macOS GUI workflow on the
   branch).

You can start a sync at any time from **Actions ▸ Sync upstream ▸ Run
workflow**, or by hand:

```bash
git remote add upstream https://github.com/mvt-project/mvt.git   # once
git fetch upstream --tags   # tags give installs from source the right version number
git checkout main
git merge upstream/main
git push origin main
```

Upstream's own workflows came with the fork. On the fork they are harmless:
PyPI publishing needs upstream's trusted-publisher setup, the Docker image
would go to this fork's own package registry, and `update-ios-data` opens
pull requests here. You can disable any of them from the Actions tab. Don't
edit or delete their files, because that would conflict with every future
sync.

## License and intended use

This wrapper is part of this MVT fork and falls under the same
[MVT License 1.1](https://docs.mvt.re/en/latest/license/). MVT exists for the
**consensual** forensic analysis of devices. Analyzing data from people who
have not consented is not permitted. MVT is a tool for investigators, not for
end-user self-assessment, and public indicators alone cannot show that a
device is clean.
