Using Docker simplifies having all the required dependencies and tools (including most recent versions of [libimobiledevice](https://libimobiledevice.org)) readily installed. Note that this requires a Linux host, as Docker for Windows and Mac [doesn't support passing through USB devices](https://docs.docker.com/desktop/faqs/#can-i-pass-through-a-usb-device-to-a-container).

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

Bind that socket into the container to let MVT communicate with the device:

```bash
docker run -it \
    --mount type=bind,source=/var/run/usbmuxd,target=/var/run/usbmuxd \
    ghcr.io/mvt-project/mvt
```

If you built the image from source, replace `ghcr.io/mvt-project/mvt` with `mvt`. 
