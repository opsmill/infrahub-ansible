#############
# Dependencies
#
#  This base stage just installs the dependencies required for production
#  without any development deps.
ARG PYTHON_VER=3.9
FROM python:${PYTHON_VER} AS base

# Allow for flexible Python versions, for broader testing
ARG PYTHON_VER=3.9
ENV PYTHON_VERSION=${PYTHON_VER}
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install --no-install-recommends -y pkg-config build-essential && \
    apt-get autoremove -y && \
    apt-get clean all && \
    rm -rf /var/lib/apt/lists/* && \
    pip --no-cache-dir install --upgrade pip wheel

WORKDIR /usr/src/app

# Update pip to latest
RUN python -m pip install -U pip

# Install poetry for dep management
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="$PATH:/root/.local/bin"
RUN poetry config virtualenvs.create false

# Bring in Poetry related files needed for other stages
COPY pyproject.toml poetry.lock ./

RUN poetry install --no-interaction --no-ansi --no-root

# Copy in the application source and everything not explicitly banned by .dockerignore
COPY . .

############
# Unit Tests
#
# This test stage runs true unit tests (no outside services) at build time, as
# well as enforcing codestyle and performing fast syntax checks. It is built
# into an image with docker-compose for running the full test suite.
FROM base AS unittests

# Set a custom collection path for all ansible commands
# Note: This only allows for one path, not colon-separated, because we use it
# elsewhere
ARG ANSIBLE_COLLECTIONS_PATH=/usr/share/ansible/collections
ENV ANSIBLE_COLLECTIONS_PATH=${ANSIBLE_COLLECTIONS_PATH}

ARG PYTHON_VER=3.9
ENV PYTHON_VERSION=${PYTHON_VER}

# Allows for custom command line arguments to be passed to ansible-test (like -vvv)
ARG ANSIBLE_SANITY_ARGS
ENV ANSIBLE_SANITY_ARGS=${ANSIBLE_SANITY_ARGS}
ARG ANSIBLE_UNIT_ARGS
ENV ANSIBLE_UNIT_ARGS=${ANSIBLE_UNIT_ARGS}

# For Module unit tests as we use some testing features avaiable in this collection
RUN ansible-galaxy collection install community.general

# Build Collection to run ansible-tests against
RUN ansible-galaxy collection build --output-path ./dist/ .

# Install built library
RUN ansible-galaxy collection install ./dist/infrahub*.tar.gz -p ${ANSIBLE_COLLECTIONS_PATH}

# Switch to the collection path for tests
WORKDIR ${ANSIBLE_COLLECTIONS_PATH}/ansible_collections/infrahub/infrahub

# Run sanity tests
RUN ansible-test sanity $ANSIBLE_SANITY_ARGS \
    --requirements \
    --skip-test pep8 \
    --python ${PYTHON_VERSION} \
    plugins/

# Run unit tests
RUN ansible-test units $ANSIBLE_UNIT_ARGS --coverage --python ${PYTHON_VERSION}

############
# Integration Tests
FROM unittests AS integration

ARG ANSIBLE_INTEGRATION_ARGS
ENV ANSIBLE_INTEGRATION_ARGS=${ANSIBLE_INTEGRATION_ARGS}
ARG infrahub_VER
ENV infrahub_VER=${infrahub_VER}

# Integration test entrypoint
ENTRYPOINT ${ANSIBLE_COLLECTIONS_PATH}/ansible_collections/infrahub/infrahub/tests/integration/entrypoint.sh

CMD ["--help"]