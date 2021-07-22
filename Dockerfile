FROM ubuntu:20.04

# Ref. https://github.com/mvt-project/mvt

# Fixing major OS dependencies
# ----------------------------
RUN apt update \
  && apt install -y python3 python3-pip libusb-1.0-0-dev \
  && apt install -y wget \ 
  && apt install -y adb \ 
  && DEBIAN_FRONTEND=noninteractive apt-get -y install default-jre-headless

# Install build tools for libimobiledevice
# ----------------------------------------
RUN apt install -y build-essential \
	checkinstall \
	git \
	autoconf \
	automake \
	libtool-bin \
	libplist-dev \
	libusbmuxd-dev \
	libssl-dev \
    pkg-config

# Clean up
# --------
RUN apt-get clean \
  && rm -rf /var/lib/apt/lists/*


# Build libimobiledevice
# ----------------------
RUN git clone https://github.com/libimobiledevice/libplist
RUN git clone https://github.com/libimobiledevice/libusbmuxd
RUN git clone https://github.com/libimobiledevice/libimobiledevice
RUN git clone https://github.com/libimobiledevice/usbmuxd

RUN cd libplist && ./autogen.sh && make && make install && ldconfig

RUN cd libusbmuxd && PKG_CONFIG_PATH=/usr/local/lib/pkgconfig ./autogen.sh && make && make install && ldconfig

RUN cd libimobiledevice && PKG_CONFIG_PATH=/usr/local/lib/pkgconfig ./autogen.sh --enable-debug && make && make install && ldconfig

RUN cd usbmuxd && PKG_CONFIG_PATH=/usr/local/lib/pkgconfig ./autogen.sh --prefix=/usr --sysconfdir=/etc --localstatedir=/var --runstatedir=/run && make && make install

# Installing MVT
# --------------
RUN pip3 install mvt

# Installing ABE
# --------------
RUN mkdir /opt/abe
RUN wget https://github.com/nelenkov/android-backup-extractor/releases/download/20210709062403-4c55371/abe.jar -O /opt/abe/abe.jar
# Create alias for abe
RUN echo 'alias abe="java -jar /opt/abe/abe.jar"' >> ~/.bashrc

# Setup investigations environment
# --------------------------------
RUN mkdir /home/cases
WORKDIR /home/cases 
RUN echo 'echo "Mobile Verification Toolkit @ Docker\n------------------------------------\n\nYou can find information about how to use this image for Android (https://github.com/mvt-project/mvt/tree/master/docs/android) and iOS (https://github.com/mvt-project/mvt/tree/master/docs/ios) in the official docs of the project.\n"' >> ~/.bashrc
RUN echo 'echo "Note that to perform the debug via USB you might need to give the Docker image access to the USB using \"docker run -it --privileged -v /dev/bus/usb:/dev/bus/usb mvt\" or, preferably, the \"--device=\" parameter.\n"' >> ~/.bashrc

CMD /bin/bash
