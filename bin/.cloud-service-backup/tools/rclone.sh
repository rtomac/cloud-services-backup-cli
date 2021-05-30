rclone_confd=${BACKUPCONFD}/rclone

function _run_rclone {
    mkdir -p ${rclone_confd}

    flags="--rm"
    [ -t 0 ] && flags+=" -i" # stdin is a terminal
    [ -t 1 ] && flags+=" -t" # stdout is a terminal

    docker run ${flags} \
        -v /etc/localtime:/etc/localtime:ro \
        -v "${rclone_confd}":/config/rclone/ \
        -v "${BACKUPDATAD}":"${BACKUPDATAD}" \
        rclone/rclone "$@"
}

function _check_rclone_remote {
    rclone_remote=${1:?rclone_remote arg required}
    _run_rclone listremotes | grep -q "${rclone_remote}:"
}
