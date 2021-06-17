# Overview

A command-line interface for backing up data from popular cloud services to a local server.

Features:
- Provides a simple and uniform CLI across all services (e.g. gmail) and irrespective of underlying tool used to back up the data (e.g. gmvault).
- Provides "copy" and "sync" modes for each service, to support both non-destructive backups as well as full syncronization.
- Automatically organizes configuration data and backup data into specified top-level directories.

# How it works

This CLI uses a combination of existing tools, vendor APIs, and custom scripts to do its work.

Makes use of the following tools:
- [rclone](http://rclone.org/), via [Docker](https://hub.docker.com/r/rclone/rclone/)
- [gmvault](http://gmvault.org/), via [Docker](https://hub.docker.com/r/rtomac/gmvault)
- [gcalvault](https://github.com/rtomac/gcalvault), via [Docker](https://hub.docker.com/r/rtomac/gcalvault)

# Commands

The following services/commands are supported:

## Gmail
`cloud-service-backup gmail (copy|sync) foo.bar@gmail.com`

## Google Calendar
`cloud-service-backup google-calendar (copy|sync) foo.bar@gmail.com`

## Google Drive
`cloud-service-backup google-drive (copy|sync) foo.bar@gmail.com`

## Google Photos
`cloud-service-backup google-photos (copy|sync) foo.bar@gmail.com 2020`

## Dropbox
`cloud-service-backup dropbox (copy|sync) foo.bar`

## Github
`cloud-service-backup github (copy|sync) foo.bar`

## Bitbucket
`cloud-service-backup bitbucket (copy|sync) foo.bar`

See the [CLI help](bin/.cloud-service-backup/USAGE.txt) for full usage and other notes.

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
```
chmod u+x ./bin/cloud-service-backup
```

## Add env variables

The CLI organizes backups and configuration in two top-level directories. See the [CLI help](bin/.cloud-service-backup/USAGE.txt) for more info.

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

# License

MIT License
