# Dockerfile to install UKAT
FROM qmentasdk/minimal:latest

# Install Dependencies
RUN apt-get update && \
    apt-get install -y wget python2.7 libglu1-mesa-dev freeglut3-dev mesa-common-dev && \
    apt-get clean -y && apt-get autoclean -y && apt-get autoremove -y

RUN wget https://fsl.fmrib.ox.ac.uk/fsldownloads/fslinstaller.py && \
    python2.7 fslinstaller.py -d /usr/local/fsl -V 6.0.5 && \
    rm -rf /usr/local/fsl/src/bin/sh 

# Get dcm2niix from github and compile
RUN cd /tmp && \
	git clone https://github.com/rordenlab/dcm2niix.git && \
	cd dcm2niix && mkdir build && cd build && \
	cmake -DBATCH_VERSION=ON -DUSE_OPENJPEG=ON .. && \
	make && make install

# Install oxasl
RUN pip install oxasl


