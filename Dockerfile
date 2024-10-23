# Base image for building libraries
# ---------------------------------
FROM ubuntu:22.04 as build-base

ARG DEBIAN_FRONTEND=noninteractive

# Install build tools and dependencies
RUN apt-get update \
  && apt-get install -y \
  build-essential \
  git \
  autoconf \
  automake \
  libtool-bin \
  pkg-config \
  libcurl4-openssl-dev \
  libusb-1.0-0-dev \
  libssl-dev \
  udev \
  && rm -rf /var/lib/apt/lists/*


# libplist
# --------
FROM build-base as build-libplist

# Build
RUN git clone https://github.com/libimobiledevice/libplist && cd libplist \
  && ./autogen.sh && make -j "$(nproc)" && make install DESTDIR=/build \
  && cd .. && rm -rf libplist


# libimobiledevice-glue
# ---------------------
FROM build-base as build-libimobiledevice-glue

# Install dependencies
COPY --from=build-libplist /build /

# Build
RUN git clone https://github.com/libimobiledevice/libimobiledevice-glue && cd libimobiledevice-glue \
  && ./autogen.sh && make -j "$(nproc)" && make install DESTDIR=/build \
  && cd .. && rm -rf libimobiledevice-glue


# libtatsu
# --------
FROM build-base as build-libtatsu

# Install dependencies
COPY --from=build-libplist /build /

# Build
RUN git clone https://github.com/libimobiledevice/libtatsu && cd libtatsu \
  && ./autogen.sh && make -j "$(nproc)" && make install DESTDIR=/build \
  && cd .. && rm -rf libtatsu


# libusbmuxd
# ----------
FROM build-base as build-libusbmuxd

# Install dependencies
COPY --from=build-libplist /build /
COPY --from=build-libimobiledevice-glue /build /

# Build
RUN git clone https://github.com/libimobiledevice/libusbmuxd && cd libusbmuxd \
  && ./autogen.sh && make -j "$(nproc)" && make install DESTDIR=/build \
  && cd .. && rm -rf libusbmuxd


# libimobiledevice
# ----------------
FROM build-base as build-libimobiledevice

# Install dependencies
COPY --from=build-libplist /build /
COPY --from=build-libtatsu /build /
COPY --from=build-libimobiledevice-glue /build /
COPY --from=build-libusbmuxd /build /

# Build
RUN git clone https://github.com/libimobiledevice/libimobiledevice && cd libimobiledevice \
  && ./autogen.sh --enable-debug && make -j "$(nproc)" && make install DESTDIR=/build \
  && cd .. && rm -rf libimobiledevice


# usbmuxd
# -------
FROM build-base as build-usbmuxd

# Install dependencies
COPY --from=build-libplist /build /
COPY --from=build-libimobiledevice-glue /build /
COPY --from=build-libusbmuxd /build /
COPY --from=build-libimobiledevice /build /

# Build
RUN git clone https://github.com/libimobiledevice/usbmuxd && cd usbmuxd \
  && ./autogen.sh --sysconfdir=/etc --localstatedir=/var --runstatedir=/run && make -j "$(nproc)" && make install DESTDIR=/build \
  && cd .. && rm -rf usbmuxd && mv /build/lib /build/usr/lib


# Create main image
FROM ubuntu:22.04 as main

LABEL org.opencontainers.image.url="https://mvt.re"
LABEL org.opencontainers.image.documentation="https://docs.mvt.re"
LABEL org.opencontainers.image.source="https://github.com/mvt-project/mvt"
LABEL org.opencontainers.image.title="Mobile Verification Toolkit"
LABEL org.opencontainers.image.description="MVT is a forensic tool to look for signs of infection in smartphone devices."
LABEL org.opencontainers.image.licenses="MVT License 1.1"
LABEL org.opencontainers.image.base.name=docker.io/library/ubuntu:22.04

# Install runtime dependencies
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
  && apt-get install -y \
  adb \
  default-jre-headless \
  libcurl4 \
  libssl3 \
  libusb-1.0-0 \
  python3 \
  sqlite3
COPY --from=build-libplist /build /
COPY --from=build-libimobiledevice-glue /build /
COPY --from=build-libtatsu /build /
COPY --from=build-libusbmuxd /build /
COPY --from=build-libimobiledevice /build /
COPY --from=build-usbmuxd /build /

# Install mvt
RUN apt-get update \
  && apt-get install -y git python3-pip \
  && PIP_NO_CACHE_DIR=1 pip3 install git+https://github.com/mvt-project/mvt.git@main \
  && apt-get remove -y python3-pip git && apt-get autoremove -y \
  && rm -rf /var/lib/apt/lists/*

# Installing ABE
ADD https://github.com/nelenkov/android-backup-extractor/releases/download/master-20221109063121-8fdfc5e/abe.jar /opt/abe/abe.jar
# Create alias for abe
RUN echo 'alias abe="java -jar /opt/abe/abe.jar"' >> ~/.bashrc

# Generate adb key folder
RUN mkdir /root/.android && adb keygen /root/.android/adbkey

# Setup investigations environment
RUN mkdir /home/cases
WORKDIR /home/cases
RUN echo 'echo "Mobile Verification Toolkit @ Docker\n------------------------------------\n\nYou can find information about how to use this image for Android (https://github.com/mvt-project/mvt/tree/master/docs/android) and iOS (https://github.com/mvt-project/mvt/tree/master/docs/ios) in the official docs of the project.\n"' >> ~/.bashrc \
  && echo 'echo "Note that to perform the debug via USB you might need to give the Docker image access to the USB using \"docker run -it --privileged -v /dev/bus/usb:/dev/bus/usb mvt\" or, preferably, the \"--device=\" parameter.\n"' >> ~/.bashrc

CMD /bin/bash
