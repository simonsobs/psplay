FROM ubuntu:18.04
MAINTAINER Xavier Garrido <xavier.garrido@lal.in2p3.fr>

RUN apt-get update && apt-get install -y \
        automake                         \
        build-essential                  \
        curl                             \
        gfortran                         \
        git                              \
        libcfitsio-dev                   \
        libfftw3-dev                     \
        libgsl-dev                       \
        libchealpix-dev                  \
        libopenmpi-dev                   \
        python3                          \
        python3-pip                      \
        wget

RUN curl -sL https://deb.nodesource.com/setup_14.x | bash -
RUN apt-get -y install nodejs

RUN ln -sfn /usr/bin/python3 /usr/bin/python

RUN useradd -m -U psplay
USER psplay
ENV USER psplay
ENV PATH "/home/psplay/.local/bin:${PATH}"
WORKDIR /home/psplay

RUN python3 -m pip install --user --upgrade pip numpy cython
RUN python3 -m pip install --user git+https://github.com/xgarrido/psplay.git

RUN jupyter labextension install plotlywidget@4.6.0 jupyterlab-plotly@4.6.0
RUN jupyter labextension install @jupyter-widgets/jupyterlab-manager @jupyter-widgets/jupyterlab-sidecar
RUN jupyter labextension install jupyter-leaflet jupyter-leaflet-car

CMD ["jupyter", "lab", "--port=8888", "--no-browser", "--ip=0.0.0.0", "--allow-root"]
