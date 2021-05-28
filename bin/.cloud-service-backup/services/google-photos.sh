function cmd_google_photos {
    google_username=${1:?google_username arg required}
    year=${2:?year arg required}

    app_slug=google_photos
    user_slug=${google_username//[^[:alnum:]]/_}
    user_backupd=${BACKUPDATAD}/${app_slug}/${user_slug}
    year_backupd=${user_backupd}/${year}
    rclone_remote=${app_slug}-${user_slug}

    if [ ! `_check_rclone_remote ${rclone_remote}` ]; then
        _run_rclone config create ${rclone_remote} "google photos" client_id "${GOOGLE_OAUTH_CLIENT_ID}" client_secret "${GOOGLE_OAUTH_CLIENT_SECRET}" scope photoslibrary.readonly config_is_local false
        echo "Created rclone remote ${rclone_remote}"
    fi

    echo "Using config at ${rclone_confd} with rclone remote ${rclone_remote}"
    echo "Backing up to ${year_backupd}"
    _run_rclone copy --stats 0 --ignore-existing "${rclone_remote}":"media/by-year/${year}" "${year_backupd}"
}
