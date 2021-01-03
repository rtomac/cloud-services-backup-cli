function _cmd_googledrive_help() {
    cat << EOF
Syncs Google Drive using rclone.

To setup:

  cloud-services-backup google-drive setup <google-username> [google-oauth-client-id] [google-oauth-client-secret]

google-username - Google username, e.g. john.doe@gmail.com
google-oauth-client-id (optional) - Google OAuth client ID to use with rclone
google-oauth-client-secret (optional) - Google OAuth client secret to use with rclone

To sync:

  cloud-services-backup google-drive sync <google-username>

google-username - Google username, e.g. john.doe@gmail.com
EOF
}

function _cmd_googledrive_init() {
    RCLONE_REMOTE="${SERVICE_SLUG}-${USERNAME_SLUG}"
    echo Using config dir ${RCLONE_CONFD} with rclone remote ${RCLONE_REMOTE}
}

# Creates rclone remote for Google Drive for user (recreates if already exists).
# Initiates OAuth authentication.
function cmd_googledrive_setup() {
    GOOGLE_OAUTH_CLIENT_ID=${1}
    GOOGLE_OAUTH_CLIENT_SECRET=${2}

    run_rclone config delete "${RCLONE_REMOTE}"
    run_rclone config create "${RCLONE_REMOTE}" drive client_id "${GOOGLE_OAUTH_CLIENT_ID}" client_secret "${GOOGLE_OAUTH_CLIENT_SECRET}" scope drive.readonly config_is_local false \
        && echo Created rclone remote ${RCLONE_REMOTE}
}

function cmd_googledrive_sync() {
    run_rclone copy --stats 0 --exclude "/Google Photos/" "${RCLONE_REMOTE}":/ "${USER_BACKUPD}"
}
