# Dockerfile to install UKAT
FROM qmentasdk/minimal:latest

# Install Dependencies
RUN apt-get update && \
    apt-get install -y wget python2.7 libglu1-mesa-dev freeglut3-dev mesa-common-dev git cmake zlib1g zlib1g-dev libjpeg-dev && \
    apt-get clean -y && apt-get autoclean -y && apt-get autoremove -y

ADD fslinstaller_mamba.py .

RUN python2.7 fslinstaller_mamba.py -d /usr/local/fsl -V 6.0.6 

# Get dcm2niix from github and compile
RUN cd /tmp && \
	git clone https://github.com/rordenlab/dcm2niix.git && \
	cd dcm2niix && mkdir build && cd build && \
	cmake -DBATCH_VERSION=ON -DUSE_OPENJPEG=ON .. && \
	make && make install

# Install oxasl
RUN pip install git+https://github.com/physimals/oxasl

# Add QMENTA interface script
Add tool.py /root

