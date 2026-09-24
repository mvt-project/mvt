# MVT for Mac: developer notes

The user guide is in the [main README](../README.md).

## Build

- Open `MVTGUI.xcodeproj` in Xcode 15 or newer, choose **My Mac** and press
  **⌘R**. No developer account is needed to run it locally.
- The app runs without the App Sandbox, because it launches MVT and reads
  acquisitions from anywhere on disk.

## Layout

- `MVTGUI/Models/`: `MVTCommand` lists each MVT command and its options.
  `CommandForm` turns a form into arguments. `AppState` handles navigation.
- `MVTGUI/Services/`: runs MVT (`ProcessRunner`), finds and updates it
  (`MVTEnvironment`), and reads the indicator sources (`IndicatorsIndex`).
- `MVTGUI/Views/`: the screens.
- `scripts/check_cli_contract.py`: checks that MVT still has everything the
  app uses (commands, flags, environment variables, output formats and
  indicator downloads).

To add an MVT option, add it to `MVTCommand`, map it in
`CommandForm.invocation()`, and list its flags in `check_cli_contract.py`.

The app can open on a given screen:
`MVTGUI.app/Contents/MacOS/MVTGUI -startScreen results -resultsFolder <path>`.
Screens: `setup`, `indicators`, `results`, or a command name such as
`iosCheckBackup` (with `-inputPath` and `-outputPath`).

## Workflows

- **macOS GUI:** builds the app and runs the contract check on every change.
- **Sync upstream:** merges
  [mvt-project/mvt](https://github.com/mvt-project/mvt) into `main` every
  day, but only after the tests, the contract check and the build pass.
  Otherwise `main` isn't touched and the run fails, which emails you.
  - This fork's README is always kept.
  - **Actions → Sync upstream → Run workflow** syncs now. It has a dry-run
    option.
- **Release macOS app:** run it with a version such as `2.0.0-beta`. It
  builds the app, tags the commit `gui-v<version>` and publishes a release.
- **Screenshots:** captures the app's screens into `screenshots/`.

Optional: a `SYNC_TOKEN` secret (a fine-grained token for this repository
with *Contents* and *Workflows* set to read and write) makes the normal
checks also run on synced commits.
