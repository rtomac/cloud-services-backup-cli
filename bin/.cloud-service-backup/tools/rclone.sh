rclone_confd=${BACKUPCONFD}/rclone

function _run_rclone {
    mkdir -p ${rclone_confd}

    docker_flags="--rm"
    [ -t 0 ] && docker_flags+=" -i" # stdin is a terminal
    [ -t 1 ] && docker_flags+=" -t" # stdout is a terminal

    echo Running: rclone $@
    docker run ${docker_flags} \
        -v /etc/localtime:/etc/localtime:ro \
        -v "${rclone_confd}":/config/rclone/ \
        -v "${BACKUPDATAD}":"${BACKUPDATAD}" \
        rclone/rclone "$@"
}

function _check_rclone_remote {
    rclone_remote=${1:?rclone_remote arg required}
    _run_rclone listremotes | grep -q "${rclone_remote}:"
}
