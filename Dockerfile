# Create main image
FROM ubuntu:24.04 AS main
COPY --from=ghcr.io/astral-sh/uv:0.11.8 /uv /uvx /usr/local/bin/

LABEL org.opencontainers.image.url="https://mvt.re"
LABEL org.opencontainers.image.documentation="https://docs.mvt.re"
LABEL org.opencontainers.image.source="https://github.com/mvt-project/mvt"
LABEL org.opencontainers.image.title="Mobile Verification Toolkit"
LABEL org.opencontainers.image.description="MVT is a forensic tool to look for signs of infection in smartphone devices."
LABEL org.opencontainers.image.licenses="MVT License 1.1"
LABEL org.opencontainers.image.base.name=docker.io/library/ubuntu:24.04

# Install runtime dependencies
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
  && apt-get install -y \
  adb \
  binutils \
  default-jre-headless \
  file \
  git \
  jq \
  less \
  libimage-exiftool-perl \
  libssl3 \
  libusb-1.0-0 \
  moreutils \
  p7zip-full \
  python3 \
  ripgrep \
  sqlite3 \
  tree \
  unzip \
  xxd \
  && rm -rf /var/lib/apt/lists/*

# Install MVT and pymobiledevice3. Native build dependencies are needed on ARM64.
ARG PYMOBILEDEVICE3_VERSION=11.12.4
COPY . mvt/
RUN apt-get update \
  && apt-get install -y --no-install-recommends build-essential python3-dev libssl-dev \
  && uv pip install --system --break-system-packages --no-cache ./mvt "pymobiledevice3==${PYMOBILEDEVICE3_VERSION}" \
  && apt-get purge -y --auto-remove build-essential python3-dev libssl-dev \
  && rm -rf mvt /var/lib/apt/lists/* \
  && pymobiledevice3 --help > /dev/null \
  && pymobiledevice3 backup2 --help > /dev/null \
  && mvt-ios --help > /dev/null

# Installing ABE
ADD --checksum=sha256:a20e07f8b2ea47620aff0267f230c3f1f495f097081fd709eec51cf2a2e11632 \
  https://github.com/nelenkov/android-backup-extractor/releases/download/master-20221109063121-8fdfc5e/abe.jar /opt/abe/abe.jar
# Create alias for abe
RUN echo 'alias abe="java -jar /opt/abe/abe.jar"' >> ~/.bashrc

# Generate adb key folder
RUN echo 'if [ ! -f /root/.android/adbkey ]; then adb keygen /root/.android/adbkey > /dev/null 2>&1; fi' >> ~/.bashrc
RUN mkdir /root/.android

# Setup investigations environment
RUN mkdir /home/cases
WORKDIR /home/cases
RUN echo 'echo "Mobile Verification Toolkit @ Docker\n------------------------------------\n\nYou can find information about how to use this image for Android (https://github.com/mvt-project/mvt/tree/master/docs/android) and iOS (https://github.com/mvt-project/mvt/tree/master/docs/ios) in the official docs of the project.\n"' >> ~/.bashrc \
  && echo 'echo "Note that to perform the debug via USB you might need to give the Docker image access to the USB using \"docker run -it --privileged -v /dev/bus/usb:/dev/bus/usb mvt\" or, preferably, the \"--device=\" parameter.\n"' >> ~/.bashrc

CMD /bin/bash
