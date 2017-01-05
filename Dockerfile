FROM base

RUN mkdir /source
WORKDIR /source
ADD build/wheelhouse /wheelhouse
ADD setup.py /source/setup.py
ADD src /source/src
RUN . /appenv/bin/activate; \
    pip install --no-index -f /wheelhouse .

# Build the dropin cache; apparently necessary to avoid premature reactor
# imports?
RUN . /appenv/bin/activate; \
    echo "Generating dropin cache..."; twist --help > /dev/null; echo "Generated.";

EXPOSE 8443
VOLUME /certificates
VOLUME /database
VOLUME /legacy-mailman-archive

ENTRYPOINT . /appenv/bin/activate; twist txlists;
