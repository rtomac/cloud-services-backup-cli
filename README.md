# Overview

A command-line interface for backing up data from popular cloud services to a local server.

Features:
- Provides a simple and uniform CLI across all services (e.g. Gmail, Google Drive) irrespective of the underlying tool being used to back up the data (e.g. gyb, rclone).
- Automatically organizes configuration data (e.g. auth tokens) and backup data into specified top-level directories.
- Provides a "setup" operation for each service, to set up and authorize the user (meant to be run once, interactively).
- Provides "copy" and "sync" operations for each service, to support both non-destructive backups as well as full synchronization (meant to be run non-interactively).

The goal of this CLI is to simply set a couple of environment variables and start backing up these services in a safe and conventional way without having to learn all the intricacies of each underlying tool. Also, for me personally, to capture this knowledge and not having to relearn it all every time my backups start to atrophy and need attention.

# How it works

This CLI uses a combination of existing tools, product APIs, and custom scripts to do its work.

Primarily makes use of the following tools:
- [rclone](http://rclone.org/)
- [got-your-back](https://github.com/GAM-team/got-your-back)
- [vdirsyncer](https://github.com/pimutils/vdirsyncer), installed via dependency

# Services

There is a plug-in model for adding services to the CLI (see the [services folder](src/cloud_services_backup_cli/services)). The following services/commands are currently implemented:

## Gmail
`cloud-service-backup gmail (setup|copy|sync) foo.bar@gmail.com`

## Google Calendar
`cloud-service-backup google-calendar (setup|copy|sync) foo.bar@gmail.com`

## Google Contacts
`cloud-service-backup google-contacts (setup|copy|sync) foo.bar@gmail.com`

## Google Drive
`cloud-service-backup google-drive (setup|copy|sync) foo.bar@gmail.com`

## Google Photos (deprecated)
`cloud-service-backup google-photos (setup|copy|sync) foo.bar@gmail.com 2020`

## Google Takeout
`cloud-service-backup google-takeout (setup|copy|sync) foo.bar@gmail.com`

## Google Photos from Takeout
`cloud-service-backup google-takeout-photos (setup|copy|sync) foo.bar@gmail.com "Photos from 2025"`

## Dropbox
`cloud-service-backup dropbox (setup|copy|sync) foo.bar`

## Github
`cloud-service-backup github (setup|copy|sync) foo.bar`

## Bitbucket
`cloud-service-backup bitbucket (setup|copy|sync) foo.bar`

See the [CLI help](src/cloud_services_backup_cli/USAGE.txt) for full usage and other notes.

# Installation and setup

## Prerequisites
- Python 3.9+
- rsync
- git
- [rclone](https://rclone.org/install/) (for Google Drive, Dropbox, etc.)
- [gyb](https://github.com/GAM-team/got-your-back/releases) (for Gmail)
- [exiftool](https://exiftool.org/) (for photos)

## Download
```
git clone https://github.com/rtomac/cloud-services-backup-cli.git
cd cloud-services-backup-cli
```

## Optionally, create virtual environment
```
virtualenv .devenv
source ./.devenv/bin/activate
```

## Install
```
pip install [-e] .
```

## Add env variables

The CLI organizes backups and configuration in two top-level directories. See the [CLI help](src/cloud_services_backup_cli/USAGE.txt) for more info.

```
export CLOUD_BACKUP_CONFD=$HOME/cloud/conf
export CLOUD_BACKUP_DATAD=$HOME/cloud/data
```

## Run setup commands

Each of these commands require authentication when first run (typically
an OAuth flow). Run each interactively the first time, unattended after that.
Each service supports a `setup` subcommand to run (or rerun) setup in isolation.

## Docker

A [Dockerfile](Dockerfile) is provided as an alternative to installing prerequisites
locally. It clones this repo and installs all dependencies. Build and run with:

```
curl -O https://raw.githubusercontent.com/rtomac/cloud-services-backup-cli/main/Dockerfile
docker build -t cloud-services-backup-cli .

docker run --rm -it \
  -v "$CLOUD_BACKUP_CONFD:$CLOUD_BACKUP_CONFD" \
  -v "$CLOUD_BACKUP_DATAD:$CLOUD_BACKUP_DATAD" \
  -e "CLOUD_BACKUP_CONFD=$CLOUD_BACKUP_CONFD" \
  -e "CLOUD_BACKUP_DATAD=$CLOUD_BACKUP_DATAD" \
  cloud-services-backup-cli help
```

Note: To run against a local repo clone (for testing), you can bind mount the repo over the installed path, e.g.:
```
  -v "$(pwd):/opt/cloud-services-backup-cli"
```

# License

MIT License
