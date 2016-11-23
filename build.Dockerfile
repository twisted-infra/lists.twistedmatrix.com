FROM base

RUN apt-get install -qy libffi-dev libssl-dev pypy-dev clang bzip2 git
RUN . /appenv/bin/activate; \
    pip install wheel

RUN mkdir /wheelhouse;
RUN mkdir /application;

ENV WHEELHOUSE=/wheelhouse
ENV PIP_WHEEL_DIR=/wheelhouse
ENV PIP_FIND_LINKS=/wheelhouse

ENTRYPOINT bash -c 'cd /application; \
           tar --warning=no-unknown-keyword -xjf - > /dev/fd/2; \
           cd /wheelhouse; \
           ls /application > /dev/fd/2; \
           (. /appenv/bin/activate; \
            pip wheel -r /application/requirements.txt; \
            pwd; \
            ls;) > /dev/fd/2; \
           tar cjf - .;'
