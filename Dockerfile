FROM python:3.13.14-slim-bookworm@sha256:9d7f287598e1a5a978c015ee176d8216435aaf335ed69ac3c38dd1bbb10e8d64

LABEL org.opencontainers.image.title="Nowlert" \
      org.opencontainers.image.description="Infrastructure Notification Engine" \
      org.opencontainers.image.vendor="Theriark" \
      org.opencontainers.image.source="https://github.com/Theriark/nowlert"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Keep the established internal root so existing mounts, state databases,
# backup archives and rollback procedures remain compatible.
WORKDIR /notifinho

COPY requirements.txt /notifinho/requirements.txt

RUN apt-get update \
    && apt-get install --no-install-recommends -y cifs-utils nfs-common \
    && rm -rf /var/lib/apt/lists/* \
    && pip install \
    --disable-pip-version-check \
    --no-cache-dir \
    -r /notifinho/requirements.txt

COPY src /notifinho/src
COPY assets /notifinho/assets
COPY tools /notifinho/tools
COPY start.sh /notifinho/start.sh

RUN python3 /notifinho/tools/validate_packaged_icons.py

# NOWLERT_* is preferred. The earlier build argument remains accepted so
# existing release automation and downstream image builds do not break.
ARG NOTIFINHO_TEAMS_ICON_BASE_URL=https://raw.githubusercontent.com/Theriark/nowlert/main/assets/icons
ARG NOWLERT_TEAMS_ICON_BASE_URL=${NOTIFINHO_TEAMS_ICON_BASE_URL}

ENV NOWLERT_TEAMS_ICON_BASE_URL=${NOWLERT_TEAMS_ICON_BASE_URL}
ENV NOTIFINHO_TEAMS_ICON_BASE_URL=${NOWLERT_TEAMS_ICON_BASE_URL}

RUN chmod +x /notifinho/start.sh

EXPOSE 8025 8080

CMD ["/notifinho/start.sh"]
