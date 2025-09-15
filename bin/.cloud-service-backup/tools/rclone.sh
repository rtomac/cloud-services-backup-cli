rclone_confd=${CLOUD_BACKUP_CONFD}/rclone

function rclone_x {
    mkdir -p ${rclone_confd}

    if command -v rclone >/dev/null 2>&1; then
        echo Running via cmd: rclone "$@"
        RCLONE_CONFIG=${rclone_confd}/rclone.conf rclone "$@"
        return
    fi

    docker_flags="--rm"
    [ -t 0 ] && docker_flags+=" -i" # stdin is a terminal
    [ -t 1 ] && docker_flags+=" -t" # stdout is a terminal

    echo Running via docker: rclone "$@"
    docker run ${docker_flags} \
        -v /etc/localtime:/etc/localtime:ro \
        -v "${rclone_confd}":/config/rclone/ \
        -v "${CLOUD_BACKUP_DATAD}":"${CLOUD_BACKUP_DATAD}" \
        rclone/rclone "$@"
}

function rclone_has_remote {
    rclone_remote=${1:?rclone_remote arg required}
    rclone_x listremotes | grep -q "${rclone_remote}:"
}
