FROM ubuntu:20.04

# Ref. https://github.com/mvt-project/mvt

LABEL url="https://mvt.re"
LABEL vcs-url="https://github.com/mvt-project/mvt"
LABEL description="MVT is a forensic tool to look for signs of infection in smartphone devices."

ENV PIP_NO_CACHE_DIR=1

# Fixing major OS dependencies
# ----------------------------
RUN apt update \
  && apt install -y python3 python3-pip libusb-1.0-0-dev \
  && apt install -y wget unzip\ 
  && DEBIAN_FRONTEND=noninteractive apt-get -y install default-jre-headless \

# Install build tools for libimobiledevice
# ----------------------------------------
  build-essential \
  checkinstall \
  git \
  autoconf \
  automake \
  libtool-bin \
  libplist-dev \
  libusbmuxd-dev \
  libssl-dev \
  sqlite3 \
  pkg-config \

# Clean up
# --------
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/* /var/cache/apt


# Build libimobiledevice
# ----------------------
RUN git clone https://github.com/libimobiledevice/libplist \
  && git clone https://github.com/libimobiledevice/libimobiledevice-glue \
  && git clone https://github.com/libimobiledevice/libusbmuxd \
  && git clone https://github.com/libimobiledevice/libimobiledevice \
  && git clone https://github.com/libimobiledevice/usbmuxd \

  && cd libplist && ./autogen.sh && make && make install && ldconfig \

  && cd ../libimobiledevice-glue && PKG_CONFIG_PATH=/usr/local/lib/pkgconfig ./autogen.sh --prefix=/usr && make && make install && ldconfig \

  && cd ../libusbmuxd && PKG_CONFIG_PATH=/usr/local/lib/pkgconfig ./autogen.sh && make && make install && ldconfig \

  && cd ../libimobiledevice && PKG_CONFIG_PATH=/usr/local/lib/pkgconfig ./autogen.sh --enable-debug && make && make install && ldconfig \

  && cd ../usbmuxd && PKG_CONFIG_PATH=/usr/local/lib/pkgconfig ./autogen.sh --prefix=/usr --sysconfdir=/etc --localstatedir=/var --runstatedir=/run && make && make install \

  # Clean up.
  && cd .. && rm -rf libplist libimobiledevice-glue libusbmuxd libimobiledevice usbmuxd

# Installing MVT
# --------------
RUN pip3 install mvt

# Installing ABE
# --------------
RUN mkdir /opt/abe \
  && wget https://github.com/nelenkov/android-backup-extractor/releases/download/20210709062403-4c55371/abe.jar -O /opt/abe/abe.jar \
# Create alias for abe
  && echo 'alias abe="java -jar /opt/abe/abe.jar"' >> ~/.bashrc

# Install Android Platform Tools 
# ------------------------------ 

RUN mkdir /opt/android \
  && wget -q https://dl.google.com/android/repository/platform-tools-latest-linux.zip \
  && unzip platform-tools-latest-linux.zip -d /opt/android \
# Create alias for adb 
  && echo 'alias adb="/opt/android/platform-tools/adb"' >> ~/.bashrc 

# Generate adb key folder 
# ------------------------------ 
RUN mkdir /root/.android && /opt/android/platform-tools/adb keygen /root/.android/adbkey

# Setup investigations environment
# --------------------------------
RUN mkdir /home/cases
WORKDIR /home/cases 
RUN echo 'echo "Mobile Verification Toolkit @ Docker\n------------------------------------\n\nYou can find information about how to use this image for Android (https://github.com/mvt-project/mvt/tree/master/docs/android) and iOS (https://github.com/mvt-project/mvt/tree/master/docs/ios) in the official docs of the project.\n"' >> ~/.bashrc \
  && echo 'echo "Note that to perform the debug via USB you might need to give the Docker image access to the USB using \"docker run -it --privileged -v /dev/bus/usb:/dev/bus/usb mvt\" or, preferably, the \"--device=\" parameter.\n"' >> ~/.bashrc

CMD /bin/bash
