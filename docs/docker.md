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


## Docker usage with Android devices

If you wish to use MVT to test an Android device you will need to enable the container's access to the host's USB devices. You can do so by enabling the `--privileged` flag and mounting the USB bus device as a volume:

```bash
docker run -it --privileged -v /dev/bus/usb:/dev/bus/usb mvt
```

**Please note:** the `--privileged` parameter is generally regarded as a security risk. If you want to learn more about this check out [this explainer on container escapes](https://blog.trailofbits.com/2019/07/19/understanding-docker-container-escapes/) as it gives access to the whole system.

Recent versions of Docker provide a `--device` parameter allowing to specify a precise USB device without enabling `--privileged`:

```bash
docker run -it --device=/dev/<your_usb_port> mvt
```
