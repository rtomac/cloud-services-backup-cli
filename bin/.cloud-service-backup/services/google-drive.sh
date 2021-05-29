function cmd_google_drive {
    google_username=${1:?google_username arg required}

    app_slug=google_drive
    user_slug=${google_username//[^[:alnum:]]/_}
    user_backupd=${BACKUPDATAD}/${app_slug}/${user_slug}
    rclone_remote=${app_slug}-${user_slug}

    if ! _check_rclone_remote "${rclone_remote}"; then
        _run_rclone config create ${rclone_remote} drive client_id "${GOOGLE_OAUTH_CLIENT_ID}" client_secret "${GOOGLE_OAUTH_CLIENT_SECRET}" scope drive.readonly config_is_local false
        echo "Created rclone remote ${rclone_remote}"
    fi

    echo "Using config at ${rclone_confd} with rclone remote ${rclone_remote}"
    echo "Backing up to ${user_backupd}"
    _run_rclone copy --stats 0 --exclude "/Google Photos/" "${rclone_remote}":/ "${user_backupd}"
}
