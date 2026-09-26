Using Docker simplifies running MVT with its dependencies readily installed. Note that this requires a Linux host, as Docker for Windows and Mac [doesn't support passing through USB devices](https://docs.docker.com/desktop/faqs/#can-i-pass-through-a-usb-device-to-a-container).

The main and iOS Docker images include pymobiledevice3 for [creating iOS backups](ios/backup/pymobiledevice3.md). You do not need to install it separately on the host. Older image tags may still include libimobiledevice instead; build from the updated source if pymobiledevice3 is unavailable.

Install Docker following the [official documentation](https://docs.docker.com/get-docker/).

Once Docker is installed, you can run MVT by downloading a prebuilt MVT Docker image, or by building a Docker image yourself from the MVT source repo.

### Using the prebuilt Docker image

```bash
docker pull ghcr.io/mvt-project/mvt
```

You can then run the Docker container with:

```
docker run -it ghcr.io/mvt-project/mvt
```


### Build and run Docker image from source

```bash
git clone https://github.com/mvt-project/mvt.git
cd mvt
docker build -t mvt .
```

Test if the image was created successfully:

```bash
docker run -it mvt
```

If a prompt is spawned successfully, you can close it with `exit`.

## Access an iOS device from Docker

On the Linux host, install and start [usbmuxd](https://github.com/libimobiledevice/usbmuxd), then connect and unlock the iOS device. The daemon exposes the device through the `/var/run/usbmuxd` socket.

Bind that socket into the container to let pymobiledevice3 communicate with the device. Also mount a local directory so acquired backups persist after the container exits:

```bash
mkdir -p "$PWD/cases"
docker run --rm -it \
    --mount type=bind,source=/var/run/usbmuxd,target=/var/run/usbmuxd \
    --mount type=bind,source="$PWD/cases",target=/home/cases \
    ghcr.io/mvt-project/mvt
```

Inside the container, verify connectivity:

```bash
pymobiledevice3 lockdown info
```

Accept the trust prompt on the unlocked device if requested. Then follow the [backup instructions](ios/backup/pymobiledevice3.md), using a destination under `/home/cases`, such as `/home/cases/backup`.

The iOS-only image defaults to running `mvt-ios`. To use pymobiledevice3 instead, override its entrypoint:

```bash
docker run --rm -it \
    --mount type=bind,source=/var/run/usbmuxd,target=/var/run/usbmuxd \
    --entrypoint pymobiledevice3 \
    ghcr.io/mvt-project/mvt:latest-ios lockdown info
```

If you built the image from source, replace `ghcr.io/mvt-project/mvt` with `mvt`. 
