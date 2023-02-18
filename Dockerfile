FROM jupyter/base-notebook:python-3.10
USER root
# Allow packages from conda-forge to be installed by default
RUN conda config --add channels conda-forge
RUN conda config --set channel_priority strict
COPY requirements.txt requirements.txt
RUN conda install --yes --file requirements.txt

# Could not download over conda so until a solution is found keeping this seperate
RUN conda install pip
RUN /opt/conda/bin/pip install wktplot suntime


