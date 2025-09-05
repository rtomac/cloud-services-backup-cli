function _run_gcardvault {
    : "${user_confd:?user_confd env variable expected}"
    : "${user_backupd:?user_backupd env variable expected}"

    mkdir -p "${user_confd}"
    mkdir -p "${user_backupd}"

    docker_flags="--rm"
    [ -t 0 ] && docker_flags+=" -i" # stdin is a terminal
    [ -t 1 ] && docker_flags+=" -t" # stdout is a terminal

    echo Running: gcardvault "$@"
    docker run ${docker_flags} \
        -v /etc/localtime:/etc/localtime:ro \
        -v "${user_confd}":/root/.gcardvault \
        -v "${user_backupd}":/root/gcardvault \
        rtomac/gcardvault "$@"
}
