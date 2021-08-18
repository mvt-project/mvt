# Check over ADB

In order to check an Android device over the [Android Debug Bridge (adb)](https://developer.android.com/studio/command-line/adb) you will first need to install [Android SDK Platform Tools](https://developer.android.com/studio/releases/platform-tools). If you have installed [Android Studio](https://developer.android.com/studio/) you should already have access to `adb` and other utilities.

While many Linux distributions already package Android Platform Tools (for example `android-platform-tools-base` on Debian), it is preferable to install the most recent version from the official website. Packaged versions might be outdated and incompatible with most recent Android handsets.

Next you will need to enable debugging on the Android device you are testing. [Please follow the official instructions on how to do so.](https://developer.android.com/studio/command-line/adb)

## Connecting over USB

The easiest way to check the device is over a USB transport. You will need to have USB debugging enabled and the device plugged into your computer. If everything is configured appropriately you should see your device when launching the command `adb devices`.

Now you can try launching MVT with:

```bash
mvt-android check-adb --output /path/to/results
```

If you have previously started an adb daemon MVT will alert you and require you to kill it with `adb kill-server` and relaunch the command.

!!! warning
    MVT relies on the Python library [adb-shell](https://pypi.org/project/adb-shell/) to connect to an Android device, which relies on libusb for the USB transport. Because of known driver issues, Windows users [are recommended](https://github.com/JeffLIrion/adb_shell/issues/118) to install appropriate drivers using [Zadig](https://zadig.akeo.ie/). Alternatively, an easier option might be to use the TCP transport and connect over Wi-Fi as describe next.

## Connecting over Wi-FI

When connecting to the device over USB is not possible or not working properly, an alternative option is to connect over the network. In order to do so, first launch an adb daemon at a fixed port number:

```bash
adb tcpip 5555
```

Then you can specify the IP address of the phone with the adb port number to MVT like so:

```bash
mvt-android check-adb --serial 192.168.1.20:5555 --output /path/to/results
```

Where `192.168.1.20` is the correct IP address of your device.

## MVT modules requiring root privileges

Of the currently available `mvt-android check-adb` modules a handful require root privileges to function correctly. This is because certain files, such as browser history and SMS messages databases are not accessible with user privileges through adb. These modules are to be considered OPTIONALLY available in case the device was already jailbroken. **Do NOT jailbreak your own device unless you are sure of what you are doing!** Jailbreaking your phone exposes it to considerable security risks!
