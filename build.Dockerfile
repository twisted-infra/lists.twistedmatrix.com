FROM base

RUN apt-get install -qy libffi-dev libssl-dev pypy-dev clang
RUN . /appenv/bin/activate; \
    pip install wheel

RUN mkdir /wheelhouse;
RUN mkdir /application;

ENV WHEELHOUSE=/wheelhouse
ENV PIP_WHEEL_DIR=/wheelhouse
ENV PIP_FIND_LINKS=/wheelhouse

ENTRYPOINT cd /application; \
           tar xjf - > /dev/fd/2; \
           cd /wheelhouse; \
            (. /appenv/bin/activate; \
             pip wheel -r /application/requirements.txt;) > /dev/fd/2 \
           tar cjf .;
