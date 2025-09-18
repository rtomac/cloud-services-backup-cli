function gcardvault_x {
    : "${user_confd:?user_confd env variable expected}"
    : "${user_backupd:?user_backupd env variable expected}"

    mkdir -p "${user_confd}"
    mkdir -p "${user_backupd}"

    if command -v gcardvault >/dev/null 2>&1; then
        # echo Running via cmd: gcardvault "$@"
        GCARDVAULT_CONF_DIR=${user_confd} GCARDVAULT_OUTPUT_DIR=${user_backupd} gcardvault "$@"
        return
    fi

    docker_flags="--rm"
    [ -t 0 ] && docker_flags+=" -i" # stdin is a terminal
    [ -t 1 ] && docker_flags+=" -t" # stdout is a terminal

    # echo Running via docker: gcardvault "$@"
    docker run ${docker_flags} \
        -v /etc/localtime:/etc/localtime:ro \
        -v /etc/timezone:/etc/timezone:ro \
        -v "${user_confd}":/root/.gcardvault \
        -v "${user_backupd}":/root/gcardvault \
        rtomac/gcardvault "$@"
}
