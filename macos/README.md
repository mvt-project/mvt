# MVT for Mac

A Mac app for the [Mobile Verification Toolkit (MVT)](https://docs.mvt.re/).
It runs MVT's checks for you without the Terminal, and shows the results in
a table.

## What you need

- A Mac with macOS 13 Ventura or newer
- Xcode 15 or newer, only if you build the app yourself
- Python 3.10 or newer: install it with `brew install python`. The Python
  that comes with Xcode is too old.

## Download

Get the latest `MVT-GUI-…-macOS.zip` from
[Releases](https://github.com/2B-4G10/MVT-GUI/releases), unzip it, and move
`MVTGUI.app` to Applications. The first time you open it, right-click the
app and choose **Open**, because it isn't notarized.

## Build the app

1. Open `macos/MVTGUI.xcodeproj` in Xcode.
2. Choose the **MVTGUI** scheme and **My Mac**.
3. Press **⌘R**.

No Apple developer account is needed to run it on your own Mac.

## First start

1. Open **Setup** and press **Install MVT**. The app installs MVT in its own
   private folder.
2. Open **Indicators** and press **Download All**.
3. Pick a check in the sidebar (iOS or Android), choose your files and press
   **Run Check**.
4. Press **View Results** when it's done.

## Indicators (IOCs)

Indicators are lists of known spyware traces, stored in STIX2 files. MVT
compares the phone's data against them.

- **Download them in the app:** open **Indicators** and press **Download
  All**, or download single sets. The app downloads every STIX2 file from
  all three official sources below. This includes files MVT's own list
  (`mvt download-iocs`) doesn't have yet, such as Amnesty's Cytrox
  indicators.
- **Choose which ones a check uses:** in any check, press **Choose
  Indicators…**. You can use all downloaded indicators (recommended), only
  the ones you pick, or add your own STIX2 files.
- **Official sources (all downloaded by the app):**
  - [mvt-indicators](https://github.com/mvt-project/mvt-indicators): the
    list the app and MVT download from
    ([index file](https://github.com/mvt-project/mvt-indicators/blob/main/indicators.yaml))
  - [Amnesty International investigations](https://github.com/AmnestyTech/investigations)
  - [Stalkerware indicators](https://github.com/AssoEchap/stalkerware-indicators)
  - [MVT documentation on indicators](https://docs.mvt.re/en/latest/iocs/)
- **Where they're stored:** `~/Library/Application Support/mvt/indicators`.

Public indicators can't prove a phone is clean. For expert help, contact
[Amnesty International's Security Lab](https://securitylab.amnesty.org/get-help/?c=mvt_docs)
or [Access Now's Digital Security Helpline](https://www.accessnow.org/help/).

## Check an iPhone

1. Make an **encrypted** backup: connect the iPhone, open it in Finder, tick
   **Encrypt local backup** and press **Back Up Now**.
2. Open **Decrypt Backup**. Choose the backup folder (in
   `~/Library/Application Support/MobileSync/Backup/`), a destination folder
   and the backup password.
3. Press **Check Decrypted Backup**, then **Run Check**.

Other iOS checks: a filesystem dump (**Check Filesystem Dump**) or a
sysdiagnose archive (**Check Sysdiagnose**).

## Check an Android phone

1. Collect the phone's data with
   [AndroidQF](https://github.com/mvt-project/androidqf).
2. Open **Check AndroidQF**, choose AndroidQF's output folder and press
   **Run Check**.

Also available: **Check Backup (SMS)**, **Check Bug Report** and **Check
Intrusion Logs**.

## Read the results

- Choose a **results folder** in a check to save its results.
- **Results** lists every alert, most severe first. Click one to see what
  triggered it.
- **Re-check Results** compares saved results against newer indicators,
  without the phone.

## Good to know

- Passwords and API keys go to MVT through environment variables, never on
  the command line.
- Only check phones whose owners have agreed. That is a condition of the
  [MVT license](https://docs.mvt.re/en/latest/license/).
- **Settings** (⌘,) lets you point the app at an MVT you installed yourself,
  for example with `pipx install mvt`.

## Keeping this fork up to date

This repository is a fork of
[mvt-project/mvt](https://github.com/mvt-project/mvt). GitHub Actions keep
it current without pull requests:

- **Sync upstream** runs every day. It merges new upstream code into `main`
  only after these pass: upstream's tests, the Mac app build, and the check
  that MVT still works the way the app expects.
- If something fails or conflicts, `main` isn't touched and GitHub emails
  you. The run page says what to do.
- **Fork setup** keeps upstream's release, Docker and bot workflows turned
  off here, since they only make sense upstream.
- To sync right now: **Actions → Sync upstream → Run workflow**.
- To sync by hand:

  ```bash
  git remote add upstream https://github.com/mvt-project/mvt.git   # once
  git fetch upstream --tags
  git merge upstream/main
  git push origin main
  ```

Optional: add a `SYNC_TOKEN` secret in **Settings → Secrets and variables →
Actions**. Use a
[fine-grained token](https://github.com/settings/personal-access-tokens/new)
for this repository with *Contents* and *Workflows* set to read and write.
It makes the normal test workflows run on synced code too.

## For developers

- **App code:** `macos/MVTGUI/`
  - `Models/MVTCommand.swift` lists each MVT command and its options.
  - `Models/CommandForm.swift` turns a form into command-line arguments.
  - `Services/` runs MVT, finds it on disk, and reads the indicator list.
  - `Views/` holds the screens.
- **Adding an MVT command or option:** add it to `MVTCommand`, map it in
  `CommandForm.invocation()`, and list its flags in
  `macos/scripts/check_cli_contract.py`.
- **Contract check:** `check_cli_contract.py` checks that the installed MVT
  still has everything the app uses: commands, flags, environment
  variables, output formats and indicator downloads. CI runs it on every
  change and before every sync.
- **Releases:** run **Actions → Release macOS app** with a version (e.g.
  `2.0.0-alpha`), or push a `gui-v…` tag. It builds the app, tags the
  commit and publishes it on the Releases page (`release-macos-gui.yml`).
- **App Sandbox:** the app runs without it, because it must launch MVT and
  read acquisitions from anywhere on disk.
