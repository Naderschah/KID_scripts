FROM conda/miniconda2
USER root


# Base config conda
RUN conda config --add channels conda-forge
RUN conda update conda

# Dependencies
RUN conda install matplotlib=2.2.4
RUN conda install scipy
RUN conda install astropy
RUN conda install ephem
RUN conda install xorg-libx11


WORKDIR /home/KID/KID_scripts/AllSkyImageProcessing/pyasb/

# The below may need to be run manually 
# RUN python setup.py install

# For CR2 -> fits conversion
RUN apt-get update
RUN apt-get install -y dcraw

# Make matplotlib use a non interactive backend
#RUN echo "backend: Agg" > ~/.config/matplotlib/matplotlibrc