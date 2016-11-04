FROM base

RUN apt-get install -qy libffi-dev libssl-dev pypy-dev clang
RUN . /appenv/bin/activate; \
    pip install wheel
RUN mkdir /wheelhouse;

ENV WHEELHOUSE=/wheelhouse
ENV PIP_WHEEL_DIR=/wheelhouse
ENV PIP_FIND_LINKS=/wheelhouse

ENTRYPOINT cd /wheelhouse; \
            (. /appenv/bin/activate; \
             pip wheel /application;) > /dev/fd/2 \
           cd /application/build/wheelhouse; \
           tar cjf .;
