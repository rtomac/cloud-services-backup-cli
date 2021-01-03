function _cmd_dropbox_help() {
    cat << EOF
Syncs Dropbox using rclone.

To setup:

  cloud-services-backup dropbox setup <dropbox-username>

dropbox-username - Dropbox username, e.g. john.doe@gmail.com

To sync:

  cloud-services-backup dropbox sync <dropbox-username>

dropbox-username - Dropbox username, e.g. john.doe@gmail.com
EOF
}

function _cmd_dropbox_init() {
    RCLONE_REMOTE="${SERVICE_SLUG}-${USERNAME_SLUG}"
    echo Using config dir ${RCLONE_CONFD} with rclone remote ${RCLONE_REMOTE}
}

# Creates rclone remote for Dropbox for user (recreates if already exists).
# Initiates OAuth authentication.
function cmd_dropbox_setup() {
    run_rclone config delete "${RCLONE_REMOTE}"
    run_rclone config create "${RCLONE_REMOTE}" dropbox config_is_local false \
        && echo Created rclone remote ${RCLONE_REMOTE}
}

function cmd_dropbox_sync() {
    run_rclone copy --stats 0 "${RCLONE_REMOTE}":/ "${USER_BACKUPD}"
}
