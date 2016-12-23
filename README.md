Overview
========
A collection of modules/commands for backing up your data from cloud services to a Linux home server. It's goal is to expose simple, comprehensible commands that can be called from a single shell script to backup all your cloud data.

Written for my personal use, but hopefully useful to others (directly, or as a reference).

Depends on
==========
[rclone](http://rclone.org/), via [Docker](https://hub.docker.com/r/kevineye/rclone/)
[gmvault](http://gmvault.org/), via [Docker](https://hub.docker.com/r/tianon/gmvault/)

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

License
=======
MIT

