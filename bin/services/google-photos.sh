function _cmd_googlephotos_help() {
    cat << EOF
Syncs Google Photos using rclone.

To setup:

  cloud-services-backup google-photos setup <google-username> [google-oauth-client-id] [google-oauth-client-secret]

google-username - Google username, e.g. john.doe@gmail.com
google-oauth-client-id (optional) - Google OAuth client ID to use with rclone
google-oauth-client-secret (optional) - Google OAuth client secret to use with rclone

To sync:

  cloud-services-backup google-photos sync <google-username> <year>

google-username - Google username, e.g. john.doe@gmail.com
year - Year of photos to sync
EOF
}

function _cmd_googlephotos_init() {
    RCLONE_REMOTE="${SERVICE_SLUG}-${USERNAME_SLUG}"
    echo Using config dir ${RCLONE_CONFD} with rclone remote ${RCLONE_REMOTE}
}

# Creates rclone remote for Google Photos for user (recreates if already exists).
# Initiates OAuth authentication.
function cmd_googlephotos_setup() {
    GOOGLE_OAUTH_CLIENT_ID=${1}
    GOOGLE_OAUTH_CLIENT_SECRET=${2}

    run_rclone config delete "${RCLONE_REMOTE}"
    run_rclone config create "${RCLONE_REMOTE}" "google photos" client_id "${GOOGLE_OAUTH_CLIENT_ID}" client_secret "${GOOGLE_OAUTH_CLIENT_SECRET}" read_only true config_is_local false \
        && echo Created rclone remote ${RCLONE_REMOTE}
}

function cmd_googlephotos_sync() {
    YEAR=${1:?Year argument required}
    run_rclone copy --stats 0 --ignore-existing "${RCLONE_REMOTE}":"media/by-year/${YEAR}" "${USER_BACKUPD}/${YEAR}"
}
