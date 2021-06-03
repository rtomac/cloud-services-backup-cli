function _run_gmvault {
    : "${user_confd:?user_confd env variable expected}"
    : "${user_backupd:?user_confd env variable expected}"

    mkdir -p "${user_confd}"
    mkdir -p "${user_backupd}"

    docker_flags="--rm"
    [ -t 0 ] && docker_flags+=" -i" # stdin is a terminal
    [ -t 1 ] && docker_flags+=" -t" # stdout is a terminal

    echo Running: gmvault $@
    docker run ${docker_flags} \
        -v /etc/localtime:/etc/localtime:ro \
        -v "${user_confd}":/root/.gmvault \
        -v "${user_backupd}":/root/gmvault-db \
        -e GOOGLEOAUTH2__GMVAULT_CLIENT_ID=${GOOGLE_OAUTH_CLIENT_ID} \
        -e GOOGLEOAUTH2__GMVAULT_CLIENT_SECRET=${GOOGLE_OAUTH_CLIENT_SECRET} \
        rtomac/gmvault "$@"
}
