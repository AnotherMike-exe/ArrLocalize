# Build stage: install the package and its one dependency into a venv.
FROM python:3.12-alpine3.24 AS build
RUN apk add --no-cache git
WORKDIR /build
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Dependencies first, so a code change does not refetch arr-service.
COPY pyproject.toml ./
RUN python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']))" > requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

COPY README.md ./
COPY src ./src
RUN pip install --no-cache-dir --no-deps .

# Runtime stage: the venv, supervisord and su-exec only.
FROM python:3.12-alpine3.24
LABEL org.opencontainers.image.source="https://github.com/AnotherMike-exe/ArrLocalize"
LABEL org.opencontainers.image.description="Copy Decypharr debrid symlinks imported by Sonarr and Radarr to permanent local files."
LABEL org.opencontainers.image.licenses="MIT"

RUN apk add --no-cache supervisor su-exec tzdata

COPY --from=build /venv /venv
COPY docker/supervisord.conf /etc/supervisord.conf
COPY docker/Entrypoint.sh docker/RunLoop.sh /usr/local/bin/
RUN chmod 755 /usr/local/bin/Entrypoint.sh /usr/local/bin/RunLoop.sh

ENV PATH="/venv/bin:$PATH" \
    PUID=99 \
    PGID=100 \
    UMASK=002 \
    TZ=Etc/UTC \
    LOCALIZE_TAG=seerr \
    LOCALIZE_INTERVAL=900 \
    LOCALIZE_EXECUTE=false \
    LOCALIZE_HISTORY_DIR=/config/history

WORKDIR /config
VOLUME ["/config"]
ENTRYPOINT ["/usr/local/bin/Entrypoint.sh"]
