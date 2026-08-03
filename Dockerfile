FROM python:3.13-alpine3.22

ARG GYB_VERSION=1.95

RUN apk add --no-cache \
        bash \
        curl \
        rsync \
        git \
        exiftool \
        rclone \
    && ln -sf python3 /usr/bin/python

# Install GYB (got-your-back) for Gmail backup
RUN bash <(curl -s -S -L https://git.io/gyb-install) -d /opt -v ${GYB_VERSION} -l
ENV PATH="/opt/gyb:$PATH"

RUN git clone https://github.com/rtomac/cloud-services-backup-cli.git /opt/cloud-services-backup-cli \
    && pip install -e /opt/cloud-services-backup-cli

ENTRYPOINT ["cloud-service-backup"]
