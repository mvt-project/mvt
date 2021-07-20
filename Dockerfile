FROM ubuntu:20.04

# Fixing major OS dependencies
# ----------------------------
RUN  apt update \
  && apt install -y python3 python3-pip libusb-1.0-0 \
  && apt install -y wget \ 
  && apt install -y adb \ 
  && DEBIAN_FRONTEND=noninteractive apt-get -y install default-jre-headless \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

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
