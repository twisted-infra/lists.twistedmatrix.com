FROM ubuntu:zesty

ARG EXTRA_APT_OPTIONS

RUN apt-get -qyy update
RUN apt-get -qyy upgrade
RUN apt-get -qyy install dirmngr

RUN apt-key adv --keyserver keyserver.ubuntu.com \
                --recv-keys 2862D0785AFACD8C65B23DB0251104D968854915
RUN echo "deb http://ppa.launchpad.net/pypy/ppa/ubuntu zesty main" > \
    /etc/apt/sources.list.d/pypy-ppa.list
RUN apt-get -qyy update ${EXTRA_APT_OPTIONS}

RUN apt-get install -qyy \
    ${EXTRA_APT_OPTIONS} \
    -o APT::Install-Recommends=false -o APT::Install-Suggests=false \
    virtualenv pypy libffi6 openssl ca-certificates git

RUN virtualenv -p /usr/bin/pypy /appenv
RUN . /appenv/bin/activate; pip install pip==9.0.1

