function gyb_x {
    : "${user_confd:?user_confd env variable expected}"
    : "${user_backupd:?user_backupd env variable expected}"

    mkdir -p "${user_confd}"
    mkdir -p "${user_backupd}"

    if command -v gyb >/dev/null 2>&1; then
        # echo Running via cmd: gyb "$@"
        gyb --config-folder "${user_confd}" --local-folder "${user_backupd}" "$@"
        return
    fi

    docker_flags="--rm"
    [ -t 0 ] && docker_flags+=" -i" # stdin is a terminal
    [ -t 1 ] && docker_flags+=" -t" # stdout is a terminal

    # echo Running via docker: gyb "$@"
    docker run ${docker_flags} \
        -v /etc/localtime:/etc/localtime:ro \
        -v /etc/timezone:/etc/timezone:ro \
        -v "${user_confd}":/config \
        -v "${user_backupd}":/data \
        -e NOCRON=1 \
        -e CONFIG_DIR=/config \
        -e DEST_DIR=/data \
        -e PUID=$(id -u) \
        -e PGID=$(id -g) \
        awbn/gyb /app/gyb "$@"
}
