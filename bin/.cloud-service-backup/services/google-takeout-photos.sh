function svc_google_takeout_photos_help {
    cat <<EOF
To do
EOF
}

function svc_google_takeout_photos_init {
    google_username=${1:?google_username arg required}

    user_slug=${google_username//[^[:alnum:]]/_}
    user_backupd_takeout="${CLOUD_BACKUP_DATAD}/google_takeout/${user_slug}/Google Photos"
    user_backupd=${CLOUD_BACKUP_DATAD}/google_takeout_photos/${user_slug}
    user_backupd_albums=${user_backupd}/albums
    user_backupd_library=${user_backupd}/library

    mkdir -p "${user_backupd}"
    mkdir -p "${user_backupd_albums}"
    mkdir -p "${user_backupd_library}"

    echo "Backing up from ${user_backupd_takeout}"
    echo "Backing up to ${user_backupd}"
}

function svc_google_takeout_photos_setup {
    if [ ! -d "${user_backupd_takeout}" ]; then
        echo "Google Photos dir in Takeout backup does not exist"
        exit 1
    fi
}

function svc_google_takeout_photos_copy { svc_google_takeout_photos_backup; }
function svc_google_takeout_photos_sync { svc_google_takeout_photos_backup; }
function svc_google_takeout_photos_backup {
    svc_google_takeout_photos_setup

    # ???
    rsync_flags=" --archive --update"
    [ "${subcommand}" == "sync" ] && rsync_flags+=" --delete"

    echo "Syncing album contents from Takeout backup..."
    for dir in "$user_backupd_takeout"/*/; do
        [ -d "$dir" ] || continue
        dirname="$(basename "$dir")"
        mkdir -p "$user_backupd_albums/$dirname"

        echo "Syncing $dirname album..."
        rsync $rsync_flags -v --exclude "*.json" "$user_backupd_takeout/$dirname/" "$user_backupd_albums/$dirname/"

        echo "Writing manifest for $dirname album..."
        python3 "${tools_path}/cmd/mk-album-manifest.py" "${user_backupd_albums}/$dirname/"
    done
}
