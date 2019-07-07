Overview
========
A collection of modules/commands for backing up your data from cloud services to a Linux home server. It's goal is to expose simple, comprehensible commands that can be called from a single shell script to backup all your cloud data.

Written for my personal use, but hopefully useful to others (directly, or as a reference).

Depends on
==========
- [rclone](http://rclone.org/), via [Docker](https://hub.docker.com/r/kevineye/rclone/)
- [gmvault](http://gmvault.org/), via [Docker](https://hub.docker.com/r/tianon/gmvault/)

Commands
========
Gmail
-----
`gmail full-sync ryan ryan.tomac@gmail.com`  
`gmail quick-sync ryan ryan.tomac@gmail.com`

Google Drive
------------
`google-drive copy ryan`  
`google-drive sync ryan`

Google Photos
-------------
`google-photos copy ryan 2016`

Dropbox
-------
`dropbox sync ryan`

Github (public repos)
---------------------
`github clone-all rtomac`

Bitbucket (public and private repos)
------------------------------------
`bitbucket set-app-password rtomac "password"`  
`bitbucket clone-all rtomac`

Installation
============
Download
--------
```
git clone https://github.com/rtomac/home-cloud-backup.git
cd home-cloud-backup
```

Make executable
---------------
`chmod -R u+x ./bin`

Add env variables
-----------------
These commands require two env variables:
- BACKUPCONFD = directory for configuration files used by scripts (auth tokens, etc.)
- BACKUPDATAD = directory for backup data

```
cat <<EOF | sudo tee -a /etc/environment
BACKUPCONFD=$HOME/cloud/conf
BACKUPDATAD=$HOME/cloud/data
EOF
```

Setup auth
----------
Most of these commands require authentication (e.g. OAuth tokens). Run each of them manually once to set that up.

Note: For gmvault, you need to setup an OAuth app & credentials of your own. The gmvault project used to have it's own, but Google no longer allows that. See:
https://github.com/gaubert/gmvault/issues/335#issuecomment-475437988

License
=======
MIT License

