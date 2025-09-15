function svc_google_drive_help {
    cat <<EOF
Backs up Google Drive using rclone with a 'drive' remote.

Subcommands:
  setup <google_username>
        Runs an auth flow with Google to create an access token.
  copy <google_username>
        Runs an 'rclone copy' that will overwrite existing files
        but will not delete files locally that have been deleted remotely.
  sync <google_username>
        Runs an 'rclone sync' that will overwrite existing files
        and delete files locally that have been deleted remotely.

OAuth2 authentication:
  If you are providing your own Google OAuth2 client (via environment
  variables), you will need to ensure the correct APIs and OAuth2 scopes
  are enabled. See:
  https://rclone.org/drive/#making-your-own-client-id
EOF
}

function svc_google_drive_init {
    google_username=${1:?google_username arg required}

    app_slug=google_drive
    user_slug=${google_username//[^[:alnum:]]/_}
    user_backupd=${CLOUD_BACKUP_DATAD}/${app_slug}/${user_slug}
    rclone_remote=${app_slug}-${user_slug}
}

function svc_google_drive_setup {
    rclone_x config create ${rclone_remote} drive client_id="${GOOGLE_OAUTH_CLIENT_ID}" client_secret="${GOOGLE_OAUTH_CLIENT_SECRET}" scope=drive.readonly teamdrive= config_is_local=false
    rclone_x config reconnect ${rclone_remote}: --auto-confirm
    echo "Created rclone remote ${rclone_remote}"
}

function svc_google_drive_copy { svc_google_drive_backup; }
function svc_google_drive_sync { svc_google_drive_backup; }
function svc_google_drive_backup {
    if ! rclone_has_remote "${rclone_remote}"; then
        svc_google_drive_setup
    fi

    echo "Using config at ${rclone_confd} with rclone remote ${rclone_remote}"
    echo "Backing up to ${user_backupd}"
    rclone_x ${subcommand} --stats-log-level NOTICE --stats 10m --exclude "/Google Photos/" "${rclone_remote}":/ "${user_backupd}"
}
