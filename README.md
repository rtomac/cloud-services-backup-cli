# Overview

A command-line interface for backing up data from popular cloud services to a local server.

Features:
- Provides a simple and uniform CLI across all services (e.g. Gmail, Google Drive) irrespective of the underlying tool being used to back up the data (e.g. gyb, rclone).
- Automatically organizations configuration data (e.g. auth tokens) and backup data into specified top-level directories.
- Provides a "setup" operation for each service, to set up and authorize the user (meant to be run once, interactively).
- Provides "copy" and "sync" operations for each service, to support both non-destructive backups as well as full synchronization (meant to be run non-interactively).

The goal of this CLI is to simply set a couple of environment variables and start backing up these services in a safe and conventional way without having to learn all the intricacies of each underlying tool. Also, for me personally, to capture this knowledge and not having to relearn it all every time my backups start to atrophy and need attention.

# How it works

This CLI uses a combination of existing tools, vendor APIs, and custom scripts to do its work.

Primarily makes use of the following tools:
- [rclone](http://rclone.org/), installed locally or via [Docker](https://hub.docker.com/r/rclone/rclone/)
- [got-your-back](https://github.com/GAM-team/got-your-back), installed locally or via [Docker](https://hub.docker.com/r/awbn/gyb)
- [gcalvault](https://github.com/rtomac/gcalvault), installed locally or via [Docker](https://hub.docker.com/r/rtomac/gcalvault)
- [gcardvault](https://github.com/rtomac/gcardvault), installed locally or via [Docker](https://hub.docker.com/r/rtomac/gcardvault)

# Services

There is a plug-in model for adding services to the CLI (see the [services folder](bin/.cloud-service-backup/services)). The following services/commands are currently implemented:

## Gmail
`cloud-service-backup gmail (setup|copy|sync) foo.bar@gmail.com`

## Google Calendar
`cloud-service-backup google-calendar (setup|copy|sync) foo.bar@gmail.com`

## Google Contacts
`cloud-service-backup google-contacts (setup|copy|sync) foo.bar@gmail.com`

## Google Drive
`cloud-service-backup google-drive (setup|copy|sync) foo.bar@gmail.com`

## Google Photos
`cloud-service-backup google-photos (setup|copy|sync) foo.bar@gmail.com 2020`

## Dropbox
`cloud-service-backup dropbox (setup|copy|sync) foo.bar`

## Github
`cloud-service-backup github (setup|copy|sync) foo.bar`

## Bitbucket
`cloud-service-backup bitbucket (setup|copy|sync) foo.bar`

See the [CLI help](bin/.cloud-service-backup/USAGE.txt) for full usage and other notes.

# Installation and setup

## Prerequisites
- Bash
- Python 3
- git

## Optional dependencies
The following are used by the CLI, but cloud-services-backup-cli will detect them and alternately fall back to running them via Docker if they are not found to be installed locally:
- rclone
- gyb
- gcardvault
- gcalvault

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
export CLOUD_BACKUP_CONFD=$HOME/cloud/conf
export CLOUD_BACKUP_DATAD=$HOME/cloud/data
```

## Run setup

Each of these command require an authentication when first run (typically
an OAuth authentication flow). Run each command interactively the first time,
unattended after that. Each service supports a `setup` subcommand to
run (or rerun) the setup on its own.

# License

MIT License
