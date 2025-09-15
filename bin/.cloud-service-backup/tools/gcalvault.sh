function gcalvault_x {
    : "${user_confd:?user_confd env variable expected}"
    : "${user_backupd:?user_backupd env variable expected}"

    mkdir -p "${user_confd}"
    mkdir -p "${user_backupd}"

    if command -v gcalvault >/dev/null 2>&1; then
        echo Running via cmd: gcalvault "$@"
        GCALVAULT_CONF_DIR=${user_confd} GCALVAULT_OUTPUT_DIR=${user_backupd} gcalvault "$@"
        return
    fi

    docker_flags="--rm"
    [ -t 0 ] && docker_flags+=" -i" # stdin is a terminal
    [ -t 1 ] && docker_flags+=" -t" # stdout is a terminal

    echo Running via docker: gcalvault "$@"
    docker run ${docker_flags} \
        -v /etc/localtime:/etc/localtime:ro \
        -v "${user_confd}":/root/.gcalvault \
        -v "${user_backupd}":/root/gcalvault \
        rtomac/gcalvault "$@"
}
