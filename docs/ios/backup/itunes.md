# Backup with iTunes app

It is possible to do an iPhone backup by using iTunes on Windows or macOS computers (in most recent versions of macOS, this feature is included in Finder).

To do that:

* Make sure iTunes is installed.
* Connect your iPhone to your computer using a Lightning/USB cable.
* Open the device in iTunes (or Finder on macOS).
* If you want to have a more accurate detection, ensure that the encrypted backup option is activated and choose a secure password for the backup.
* Start the backup and wait for it to finish (this may take up to 30 minutes).

![](../../../img/macos-backup.jpg)
_Source: [Apple Support](https://support.apple.com/en-us/HT211229)_

* Once the backup is done, find its location and copy it to a place where it can be analyzed by MVT. On Windows, the backup can be stored either in `%USERPROFILE%\Apple\MobileSync\` or `%USERPROFILE%\AppData\Roaming\Apple Computer\MobileSync\`. On macOS, the backup is stored in `~/Library/Application Support/MobileSync/`.
