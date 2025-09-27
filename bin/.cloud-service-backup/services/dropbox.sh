function svc_dropbox_help {
    cat <<EOF
Backs up Dropbox using rclone with a 'dropbox' remote.

Subcommands:
  setup <dropbox_username>
        Runs an auth flow with Dropbox to create an access token.
  copy <dropbox_username>
        Runs an 'rclone copy' that will overwrite existing files
        but will not delete files locally that have been deleted remotely.
  sync <dropbox_username>
        Runs an 'rclone sync' that will overwrite existing files
        and delete files locally that have been deleted remotely.
EOF
}

function svc_dropbox_init {
    dropbox_username=${1:?dropbox_username arg required}

    app_slug=dropbox
    user_slug=${dropbox_username//[^[:alnum:]]/_}
    user_backupd=${CLOUD_BACKUP_DATAD}/${app_slug}/${user_slug}
    rclone_remote=${app_slug}+${user_slug}

    mkdir -p "${user_backupd}"

    echo "Using rclone remote ${rclone_remote} with config at ${RCLONE_CONFIG}"
    echo "Backing up to ${user_backupd}"
}

function svc_dropbox_setup {
    # config_is_local=false will skip authz and make non-interactive
    rclone_x config create ${rclone_remote} dropbox config_is_local=false
    rclone_authorize_user "${rclone_remote}"
    echo "Created rclone remote ${rclone_remote}"
}

function svc_dropbox_copy { svc_dropbox_backup; }
function svc_dropbox_sync { svc_dropbox_backup; }
function svc_dropbox_backup {
    if ! rclone_has_remote "${rclone_remote}"; then
        svc_dropbox_setup
    fi

    echo "Starting rclone ${subcommand}..."
    rclone_x ${subcommand} --stats-log-level NOTICE --stats 10m "${rclone_remote}":/ "${user_backupd}"
}
