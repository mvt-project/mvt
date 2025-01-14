# Installation

Before proceeding, please note that MVT requires Python 3.6+ to run. While it should be available on most operating systems, please make sure of that before proceeding.

## Dependencies on Linux

First install some basic dependencies that will be necessary to build all required tools:

```bash
sudo apt install python3 python3-venv python3-pip sqlite3 libusb-1.0-0
```

*libusb-1.0-0* is not required if you intend to only use `mvt-ios` and not `mvt-android`.

(Recommended) Set up `pipx`

For Ubuntu 23.04 or above:
```bash
sudo apt install pipx
pipx ensurepath
```

For Ubuntu 22.04 or below:
```
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

Other distributions: check for a `pipx` or `python-pipx` via your package manager.

When working with Android devices you should additionally install [Android SDK Platform Tools](https://developer.android.com/studio/releases/platform-tools). If you prefer to install a package made available by your distribution of choice, please make sure the version is recent to ensure compatibility with modern Android devices.

## Dependencies on macOS

Running MVT on macOS requires Xcode and [homebrew](https://brew.sh) to be installed.

In order to install dependencies use:

```bash
brew install python3 pipx libusb sqlite3
```

*libusb* is not required if you intend to only use `mvt-ios` and not `mvt-android`.

When working with Android devices you should additionally install [Android SDK Platform Tools](https://developer.android.com/studio/releases/platform-tools):

```bash
brew install --cask android-platform-tools
```

Or by downloading the [official binary releases](https://developer.android.com/studio/releases/platform-tools).

## MVT on Windows

MVT does not currently officially support running natively on Windows. While most functionality should work out of the box, there are known issues especially with `mvt-android`.

It is recommended to try installing and running MVT from [Windows Subsystem Linux (WSL)](https://docs.microsoft.com/en-us/windows/wsl/about) and follow Linux installation instructions for your distribution of choice.

## Installing MVT

### Installing from PyPI with pipx (recommended)
1. Install `pipx` following the instructions above for your OS/distribution. Make sure to run `pipx ensurepath` and open a new terminal window.
2. ```bash
   pipx install mvt
   ```

You now should have the `mvt-ios` and `mvt-android` utilities installed. If you run into problems with these commands not being found, ensure you have run `pipx ensurepath` and opened a new terminal window.

### Installing from PyPI directly into a virtual environment
You can use `pipenv`, `poetry` etc. for your virtual environment, but the provided example is with the built-in `venv` tool:

1. Create the virtual environment in a folder in the current directory named `env`:
```bash
python3 -m venv env
```

2. Activate the virtual environment:
```bash
source env/bin/activate
```

3. Install `mvt` into the virtual environment:
```bash
pip install mvt
```

The `mvt-ios` and `mvt-android` utilities should now be available as commands whenever the virtual environment is active.

### Installing from git source with pipx
If you want to have the latest features in development, you can install MVT directly from the source code in git.

```bash
pipx install --force git+https://github.com/mvt-project/mvt.git
```

You now should have the `mvt-ios` and `mvt-android` utilities installed.

**Notes:**
1. The `--force` flag is necessary to force the reinstallation of the package.
2. To revert to using a PyPI version, it will be necessary to `pipx uninstall mvt` first.

## Setting up command completions

See ["Command completions"](command_completion.md)
