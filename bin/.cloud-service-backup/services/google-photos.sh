function svc_google_photos_help {
    cat <<EOF
Backs up Google Photos using rclone with a 'google photos' remote.

WARNING: rclone uses Google Photos API, which has significant limitations,
preventing a full backup of photos and videos. Unfortunately it's
not that useful any more. See:
https://rclone.org/googlephotos/

Subcommands:
  setup <google_username>
        Runs an auth flow with Google to create an access token.
  copy <google_username> <year>
        Runs an 'rclone copy' for photos in the specified year
        that will add new photos but will not delete photos locally
        that have been deleted remotely.
  sync <google_username> <year>
        Runs an 'rclone sync' for photos in the specified year
        that will add new photos and delete photos locally
        that have been deleted remotely.

OAuth2 authentication:
  If you are providing your own Google OAuth2 client (via environment
  variables), you will need to ensure the correct APIs and OAuth2 scopes
  are enabled. See:
  https://rclone.org/googlephotos/#making-your-own-client-id
EOF
}

function svc_google_photos_init {
    google_username=${1:?google_username arg required}
    year=${2:?year arg required}

    app_slug=google_photos
    user_slug=${google_username//[^[:alnum:]]/_}
    user_backupd=${CLOUD_BACKUP_DATAD}/${app_slug}/${user_slug}
    year_backupd=${user_backupd}/${year}
    rclone_remote=${app_slug}+${user_slug}

    mkdir -p "${user_backupd}"

    echo "Using rclone remote ${rclone_remote} with config at ${RCLONE_CONFIG}"
    echo "Backing up to ${user_backupd}"
}

function svc_google_photos_setup {
    # config_is_local=false will skip authz and make non-interactive
    rclone_x config create ${rclone_remote} "google photos" \
        client_id="${GOOGLE_OAUTH_CLIENT_ID}" client_secret="${GOOGLE_OAUTH_CLIENT_SECRET}" \
        scope=photoslibrary.readonly config_is_local=false
    rclone_authorize_user "${rclone_remote}"
    echo "Created rclone remote ${rclone_remote}"
}

function svc_google_photos_copy { svc_google_photos_backup; }
function svc_google_photos_sync { svc_google_photos_backup; }
function svc_google_photos_backup {
    if ! rclone_has_remote "${rclone_remote}"; then
        svc_google_photos_setup
    fi

    flags=""
    [ "${subcommand}" == "copy" ] && flags+=" --ignore-existing"

    rclone_x ${subcommand} --stats-log-level NOTICE --stats 10m ${flags} "${rclone_remote}":"media/by-year/${year}" "${year_backupd}"
}
