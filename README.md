# Overview

A CLI for backing up data from popular cloud services to a local server.

Written for my personal use, but hopefully useful to others.

# Makes use of

- [rclone](http://rclone.org/), via [Docker](https://hub.docker.com/r/rclone/rclone/)
- [gmvault](http://gmvault.org/), via [Docker](https://hub.docker.com/r/tianon/gmvault/)

# Commands

## Gmail
`cloud-service-backup gmail foo.bar@gmail.com [update|sync]`
## Google Drive
`cloud-service-backup google-drive foo.bar@gmail.com [update|sync]`
## Google Photos
`cloud-service-backup google-photos foo.bar@gmail.com <year> [update|sync]`
## Dropbox
`cloud-service-backup dropbox foo.bar@gmail.com [update|sync]`
## Github
`cloud-service-backup github foo.bar [update|sync]`
## Bitbucket
`cloud-service-backup bitbucket foo.bar [update|sync]`

# Installation

## Prerequisites
- Docker engine
- Python 3
- git

## Download
```
git clone https://github.com/rtomac/cloud-services-backup-cli.git
cd cloud-services-backup-cli
```

## Make executable
`chmod u+x ./bin/cloud-service-backup`

## Add env variables

The CLI organizes backups and configuration in the following
two directories. These environment variables are required.
- BACKUPCONFD = directory for configuration files used by scripts (auth tokens, etc.)
- BACKUPDATAD = directory for backup data

```
cat <<EOF | sudo tee -a /etc/environment
BACKUPCONFD=$HOME/cloud/conf
BACKUPDATAD=$HOME/cloud/data
EOF
```

## Run setup

Each of these command require an authentication when first run (typically
an OAuth authentication flow). Run each command interactively the first time,
unattended after that.

License
=======
MIT License
