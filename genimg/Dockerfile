FROM python:latest

ENV HOME /root
WORKDIR $HOME

RUN python3 -m pip install --no-cache-dir notebook jupyterlab
RUN pip install ipython jupyter jupyterlab-language-pack-ja-JP jupyterlab-fonts

RUN apt-get update && apt-get install -y --no-install-recommends \
    m4 \
    bison \
    flex \
    libfl-dev \
    libfl2 \
    libbison-dev

EXPOSE 8888

WORKDIR $HOME/uec-lexyacc
ADD . $HOME/uec-lexyacc


ARG NB_USER=uecstudent
ARG NB_UID=1000
ENV USER ${NB_USER}
ENV NB_UID ${NB_UID}
ENV HOME /home/${NB_USER}

RUN adduser --disabled-password \
    --gecos "Default user" \
    --uid ${NB_UID} \
    ${NB_USER}

USER root

RUN mkdir -p /home/${NB_USER}/uec-lexyacc/lexyacc-kernel
COPY LexYaccKernel.py /home/${NB_USER}/uec-lexyacc
COPY lexyacc-kernel /home/${NB_USER}/uec-lexyacc/lexyacc-kernel
RUN jupyter kernelspec install /home/${NB_USER}/uec-lexyacc/lexyacc-kernel
COPY notebooks /home/${NB_USER}

RUN chown -R ${NB_UID} ${HOME}

USER ${NB_USER}
WORKDIR ${HOME}

# CMD ["jupyter", "notebook", "--no-browser", "--allow-root", "--ip='0.0.0.0'"]