FROM base

ADD build/wheelhouse /wheelhouse
RUN . /appenv/bin/activate; \
    pip install --no-index -f wheelhouse rproxy

# Build the dropin cache; apparently necessary to avoid premature reactor
# imports?
RUN . /appenv/bin/activate; \
    twist --help; echo 'again?'; twist --help;

VOLUME /conf

EXPOSE 8000
EXPOSE 8443

ENTRYPOINT . /appenv/bin/activate; \
           twist web;
