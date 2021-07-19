# Installation

Before proceeding, please note that mvt requires Python 3.6+ to run. While it should be available on most operating systems, please make sure of that before proceeding.

## Dependencies on Linux

First install some basic dependencies that will be necessary to build all required tools:

```bash
sudo apt install python3 python3-pip libusb-1.0-0
```

*libusb-1.0-0* is not required if you intend to only use `mvt-ios` and not `mvt-android`.

For running on NixOS, a `shell.nix` is supplied.

## Dependencies on Mac

Running MVT on Mac requires Xcode and [homebrew](https://brew.sh) to be installed.

In order to install dependencies use:

```bash
brew install python3 libusb
```

*libusb* is not required if you intend to only use `mvt-ios` and not `mvt-android`.

## Installing MVT

If you haven't done so, you can add this to your `.bashrc` or `.zshrc` file in order to add locally installed Pypi binaries to your `$PATH`:

```bash
export PATH=$PATH:~/.local/bin
```

Then you can install MVT directly from [pypi](https://pypi.org/project/mvt/)

```bash
pip install mvt
```

Or from the source code:

```bash
git clone https://github.com/mvt-project/mvt.git
cd mvt
pip3 install .
```

You now should have the `mvt-ios` and `mvt-android` utilities installed.
