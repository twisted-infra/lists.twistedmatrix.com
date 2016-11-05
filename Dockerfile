FROM base

ADD build/wheelhouse /wheelhouse
ADD requirements.txt requirements.txt
RUN . /appenv/bin/activate; \
    pip install --no-index -f wheelhouse -r requirements.txt

# Build the dropin cache; apparently necessary to avoid premature reactor
# imports?
RUN . /appenv/bin/activate; \
    twist --help; echo 'again?'; twist --help;

EXPOSE 8443
VOLUME /certificates

ENTRYPOINT . /appenv/bin/activate; twist txlists;
