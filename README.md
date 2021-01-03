# Overview

A CLI for backing up your data from popular cloud services to a home server.

Written for my personal use, but hopefully useful to others.

# Makes use of

- [rclone](http://rclone.org/), via [Docker](https://hub.docker.com/r/rclone/rclone/)
- [gmvault](http://gmvault.org/), via [Docker](https://hub.docker.com/r/tianon/gmvault/)

# Commands

## Gmail

`cloud-services-backup gmail john.doe@gmail.com setup`

`cloud-services-backup gmail john.doe@gmail.com sync`

## Google Drive

`cloud-services-backup google-drive john.doe@gmail.com setup`

`cloud-services-backup google-drive john.doe@gmail.com sync`

## Google Photos

`cloud-services-backup google-photos john.doe@gmail.com setup`

`cloud-services-backup google-photos john.doe@gmail.com sync 2021`

## Dropbox

`cloud-services-backup dropbox john.doe@gmail.com setup`

`cloud-services-backup dropbox john.doe@gmail.com sync`

## Github

`cloud-services-backup github john.doe setup my_personal_access_token`

`cloud-services-backup github john.doe sync`

## Bitbucket

`cloud-services-backup bitbucket john.doe@gmail.com setup my_app_password`

`cloud-services-backup bitbucket john.doe@gmail.com sync`

# Installation

## Prerequisites
- Docker engine
- Python 3

## Download
```
git clone https://github.com/rtomac/home-cloud-backup.git
cd home-cloud-backup
```

## Make executable
`chmod -R u+x ./bin`

## Add env variables
These commands require two env variables:
- BACKUPCONFD = directory for configuration files used by scripts (auth tokens, etc.)
- BACKUPDATAD = directory for backup data

```
cat <<EOF | sudo tee -a /etc/environment
BACKUPCONFD=$HOME/cloud/conf
BACKUPDATAD=$HOME/cloud/data
EOF
```

## Run setups
All of these commands require authentication, which is typically an interactive authentication to complete an OAuth authentication flow. Run `setup` for each service interactively to set that up.

License
=======
MIT License
