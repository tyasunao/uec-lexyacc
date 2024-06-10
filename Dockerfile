FROM python:latest

ENV HOME /root
WORKDIR $HOME

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
RUN jupyter kernelspec install lexyacc-kernel

CMD ["jupyter", "notebook", "--no-browser", "--allow-root", "--ip='0.0.0.0'"]