# Runs an `rclone copy` or `rclone sync`.
#
# In "copy" mode, copies all new files from Google Photos
# to local, but does not copy modified files (considered unlikely)
# or delete files locally (protects against accidental or malicious
# deletion in Google Photos).

# In "sync" mode, copies all new and modified files and deletes
# all files locally which have been deleted in Google Photos.
function cmd_google_photos {
    google_username=${1:?google_username arg required}
    year=${2:?year arg required}
    mode=${3:-copy}
    [ "${mode}" != "copy" ] && [ "${mode}" != "sync" ] && echo "Invalid mode" && exit 1

    app_slug=google_photos
    user_slug=${google_username//[^[:alnum:]]/_}
    user_backupd=${BACKUPDATAD}/${app_slug}/${user_slug}
    year_backupd=${user_backupd}/${year}
    rclone_remote=${app_slug}-${user_slug}

    if ! _check_rclone_remote "${rclone_remote}"; then
        _run_rclone config create ${rclone_remote} "google photos" client_id "${GOOGLE_OAUTH_CLIENT_ID}" client_secret "${GOOGLE_OAUTH_CLIENT_SECRET}" scope photoslibrary.readonly config_is_local false
        echo "Created rclone remote ${rclone_remote}"
    fi

    operation=copy
    flags=""
    [ "${mode}" == "sync" ] && operation=sync
    [ "${mode}" == "copy" ] && flags+=" --ignore-existing"

    echo "Using config at ${rclone_confd} with rclone remote ${rclone_remote}"
    echo "Backing up to ${year_backupd}"
    _run_rclone ${operation} --stats-log-level NOTICE --stats 10m ${flags} "${rclone_remote}":"media/by-year/${year}" "${year_backupd}"
}
