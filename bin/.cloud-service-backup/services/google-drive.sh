# Runs an `rclone copy` or `rclone sync`.
#
# In "copy" mode, copies all new and modified files from Google Drive
# to local, but does not delete files locally (protects
# against accidental or malicious deletion in Google Drive).
#
# In "sync" mode, copies all new and modified files and deletes
# all files locally which have been deleted in Google Drive.
function cmd_google_drive {
    google_username=${1:?google_username arg required}
    mode=${2:-copy}
    [ "${mode}" != "copy" ] && [ "${mode}" != "sync" ] && echo "Invalid mode" && exit 1

    app_slug=google_drive
    user_slug=${google_username//[^[:alnum:]]/_}
    user_backupd=${BACKUPDATAD}/${app_slug}/${user_slug}
    rclone_remote=${app_slug}-${user_slug}

    if ! _check_rclone_remote "${rclone_remote}"; then
        _run_rclone config create ${rclone_remote} drive client_id "${GOOGLE_OAUTH_CLIENT_ID}" client_secret "${GOOGLE_OAUTH_CLIENT_SECRET}" scope drive.readonly config_is_local false
        echo "Created rclone remote ${rclone_remote}"
    fi

    operation=copy
    [ "${mode}" == "sync" ] && operation=sync

    echo "Using config at ${rclone_confd} with rclone remote ${rclone_remote}"
    echo "Backing up to ${user_backupd}"
    _run_rclone ${operation} --stats-log-level NOTICE --stats 10m --exclude "/Google Photos/" "${rclone_remote}":/ "${user_backupd}"
}
