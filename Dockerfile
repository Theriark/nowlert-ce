FROM python:3.13.14-slim-bookworm@sha256:9d7f287598e1a5a978c015ee176d8216435aaf335ed69ac3c38dd1bbb10e8d64

LABEL org.opencontainers.image.title="Nowlert" \
      org.opencontainers.image.description="Infrastructure Notification Engine" \
      org.opencontainers.image.vendor="Theriark" \
      org.opencontainers.image.source="https://github.com/Theriark/nowlert"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /nowlert

COPY requirements.txt /nowlert/requirements.txt

RUN apt-get update \
    && apt-get install --no-install-recommends -y cifs-utils nfs-common \
    && rm -rf /var/lib/apt/lists/* \
    && pip install \
    --disable-pip-version-check \
    --no-cache-dir \
    -r /nowlert/requirements.txt

COPY src /nowlert/src
COPY assets /nowlert/assets
COPY tools /nowlert/tools
COPY start.sh /nowlert/start.sh

RUN python3 /nowlert/tools/validate_packaged_icons.py

ARG NOWLERT_TEAMS_ICON_BASE_URL=https://raw.githubusercontent.com/Theriark/nowlert/main/assets/icons

ENV NOWLERT_TEAMS_ICON_BASE_URL=${NOWLERT_TEAMS_ICON_BASE_URL}

RUN chmod +x /nowlert/start.sh

EXPOSE 8025 8080

CMD ["/nowlert/start.sh"]
