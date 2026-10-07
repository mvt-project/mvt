# Install pymobiledevice3

Before acquiring data from an iOS device, we recommend installing [pymobiledevice3](https://github.com/doronz88/pymobiledevice3). It provides command-line tools for generating iTunes-compatible backups and extracting crash logs.

## Installation

Install `pipx` following the [MVT installation instructions](../install.md), then run:

```bash
pipx install pymobiledevice3
```

To update an existing installation:

```bash
pipx upgrade pymobiledevice3
```

On Linux, you also need `usbmuxd` to communicate with devices over USB. On Debian and Ubuntu, install it with:

```bash
sudo apt install usbmuxd
```

macOS includes the required USB device service. For other platforms and additional requirements, see the [pymobiledevice3 installation documentation](https://doronz88.github.io/pymobiledevice3/installation/).

## Verify connectivity

Connect the iOS device to your computer with a USB cable and unlock it. Accept the **Trust This Computer** prompt and enter the device passcode if requested. Then run:

```bash
pymobiledevice3 usbmux list
pymobiledevice3 lockdown info
```

These commands should list the connected device and display its details. If pairing is needed, run:

```bash
pymobiledevice3 lockdown pair
```

If no device is found, check the USB connection, make sure the device is unlocked, and, on Linux, check that `usbmuxd` is running. See the [upstream troubleshooting guide](https://doronz88.github.io/pymobiledevice3/guides/troubleshooting/) for further help.

Once connected, follow the [backup instructions](backup/pymobiledevice3.md).
