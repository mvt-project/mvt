# Install libimobiledevice

Before proceeding with doing any acquisition of iOS devices we recommend installing [libimobiledevice](https://www.libimobiledevice.org/) utilities. These utilities will become useful when extracting crash logs and generating iTunes backups. Because the utilities and its libraries are subject to frequent changes in response to new versions of iOS, you might want to consider compiling libimobiledevice utilities from sources. Otherwise, if available, you can try installing packages available in your distribution:

```bash
sudo apt install libimobiledevice-utils
```

On Mac, you can try installing it from brew:

```bash
brew install --HEAD libimobiledevice
```

If you have a reasonably recent version of libimobiledevice in your package manager, it might work straight out of the box. Try connecting your iOS device to your computer via USB and run:

```bash
ideviceinfo
```

If you encounter unexpected issues, uninstall the packages and try compiling libimobiledevcice from sources.

## Compile libimobiledevice from sources

!!! warning
    The following instructions are a best effort. The installation from source requires several steps, and it is likely some have been forgotten here and that won't work for you. You will likely need to fiddle around a bit before getting this right.

Make sure you have uninstalled all the libimobiledevice tools from your package manage:

```bash
sudo apt remove --purge libimobiledevice-utils libimobiledevice-dev libimobiledevice6 libplist-dev libplist3 libusbmuxd-dev libusbmuxd-tools libusbmuxd4 libusbmuxd6 usbmuxd
```

Firstly you need to install [libplist](https://github.com/libimobiledevice/libplist). Then you can install [libusbmuxd](https://github.com/libimobiledevice/libusbmuxd).

Now you should be able to to download and install the actual suite of tools at [https://github.com/libimobiledevice/libimobiledevice](https://github.com/libimobiledevice/libimobiledevice).

You can now also build and install [usbmuxd](https://github.com/libimobiledevice/usbmuxd).

## Making sure everything works fine.

Once the idevice tools are available you can check if everything works fine by connecting your iOS device and running:

```bash
ideviceinfo
```

This should some many details on the connected iOS device. If you are connecting the device to your laptop for the first time, it will require to unlock and enter the PIN code on the mobile device. If it complains that no device is connected and the mobile device is indeed plugged in through the USB cable, you might need to do this first, although typically the pairing is automatically done when connecting the device:

```bash
sudo usbmuxd -f -d
idevicepair pair
```

Again, it will ask to unlock the phone and enter the PIN code. 
