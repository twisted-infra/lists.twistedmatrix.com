FROM base

ADD build/wheelhouse /wheelhouse
RUN . /appenv/bin/activate; \
    pip install --no-index -f wheelhouse -r requirements.txt

# Build the dropin cache; apparently necessary to avoid premature reactor
# imports?
RUN . /appenv/bin/activate; \
    twist --help; echo 'again?'; twist --help;

EXPOSE 8080

ENTRYPOINT . /appenv/bin/activate; \
           twist web;
