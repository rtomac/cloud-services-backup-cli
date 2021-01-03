RCLONE_CONFD=${BACKUPCONFD}/rclone

# Runs gmvault via rclone/rclone image.
# All args passed to rclone.
function run_rclone {
    : "${BACKUPDATAD:?Environment variable BACKUPDATAD is expected}"

    mkdir -p ${RCLONE_CONFD}

    docker run -it --rm \
        --log-driver syslog \
        -v "$RCLONE_CONFD":/root \
        -v "$BACKUPDATAD":"$BACKUPDATAD" \
        rclone/rclone "$@"
}
