<p align="center">
     <img src="./docs/mvt.png" width="300" />
</p>

# Mobile Verification Toolkit

[![](https://img.shields.io/pypi/v/mvt)](https://pypi.org/project/mvt/)

Mobile Verification Toolkit (MVT) is a collection of utilities to simplify and automate the process of gathering forensic traces helpful to identify a potential compromise of Android and iOS devices.

[Please check out the documentation](https://mvt-docs.readthedocs.io/en/latest/)..

### Installation using the Docker image

Using Docker is the easiest way of having all the dependencies fixed with a couple of commands.
Install Docker using the [official instructions](https://docs.docker.com/get-docker/) provided in the Website page.

Afterwards, you can build the Docker image once inside:

```
bash
git clone https://github.com/mvt-project/mvt.git
cd mvt
docker build -t mvt .
```

Once the image is built, can now be tested using, what will prompt a bash terminal:

```bash
docker run -it mvt
```

If this is correct, close the container (`exit`) and it is time to connect the Android device to analyse to the USB port using the development mode as explained in the official docs [here](https://developer.android.com/studio/debug/dev-options).
To have visibility of the USB, the container WILL need to have access to the USB which is not activated in Docker by default.
This can be done using the `--privileged` parameter when launching Docker as follows and mounting the USB as a volume.

```bash
docker run -it --privileged -v /dev/bus/usb:/dev/bus/usb mvt
```

Note that using the `--pivileged` parameter is insecure for a number of reasons explained in detail [here](https://blog.trailofbits.com/2019/07/19/understanding-docker-container-escapes/) as it gives access to the whole system.
As a brief explanation, the `-v <host_path>:<docker_path>` syntax maps the host path to the dockerized path to allow the connection.
Modern versions of Docker have a `--device` option where you can specify the exact USB to mount without the `--privileged` option:

```bash
docker run -it --device=/dev/<your_usb_port> mvt
```

The Docker image contains the dependencies fixed to perform a forensic analysis on an Android device using MVT, including ADB (reachable using `adb` as expected) and ABE (installed under `/opt/abe` and reachable using `abe` from the command line) which is ready to be launched using the installed version of Java. 
Thus, the forensic analyst can proceed as expected to grab the evidences needed and performs the required tests.

## Manual Installation

First you need to install dependencies, on Linux `sudo apt install python3 python3-pip libusb-1.0-0` or on MacOS `brew install python3 libusb`.

Then you can install mvt from pypi with `pip install mvt`, or directly form sources:
```bash
git clone https://github.com/mvt-project/mvt.git
cd mvt
pip3 install .
```

## Usage

MVT provides two commands `mvt-ios` and `mvt-android` with the following subcommands available:
* `mvt-ios`:
    * `check-backup`: Extract artifacts from an iTunes backup
    * `check-fs`: Extract artifacts from a full filesystem dump
    * `check-iocs`: Compare stored JSON results to provided indicators
    * `decrypt-backup`:  Decrypt an encrypted iTunes backup
* `mvt-android`:
    * `check-backup`: Check an Android Backup
    * `download-apks`: Download all or non-safelisted installed APKs

Check out [the documentation to see how to use them.](https://mvt-docs.readthedocs.io/en/latest/).


## License

The purpose of MVT is to facilitate the ***consensual forensic analysis*** of devices of those who might be targets of sophisticated mobile spyware attacks, especially members of civil society and marginalized communities. We do not want MVT to enable privacy violations of non-consenting individuals. Therefore, the goal of this license is to prohibit the use of MVT (and any other software licensed the same) for the purpose of *adversarial forensics*.

In order to achieve this, MVT is released under an adaptation of [Mozilla Public License v2.0](https://www.mozilla.org/MPL). This modified license includes a new clause 3.0, "Consensual Use Restriction" which permits the use of the licensed software (and any *"Larger Work"* derived from it) exclusively with the explicit consent of the person/s whose data is being extracted and/or analysed (*"Data Owner"*).

[Read the LICENSE](https://github.com/mvt-project/mvt/blob/main/LICENSE)
