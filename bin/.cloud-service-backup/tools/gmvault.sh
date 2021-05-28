function _run_gmvault {
    : "${user_confd:?user_confd env variable expected}"
    : "${user_backupd:?user_confd env variable expected}"

    mkdir -p "${user_confd}"
    mkdir -p "${user_backupd}"

    docker build -t gmvault_arm64 github.com/rtomac/gmvault-docker-arm64.git#main > /dev/null
    docker run -it --rm \
        -v /etc/localtime:/etc/localtime:ro \
        -v "${user_confd}":/root/.gmvault \
        -v "${user_backupd}":/root/gmvault-db \
        -e GMVAULT_CLIENT_ID=${GOOGLE_OAUTH_CLIENT_ID} \
        -e GMVAULT_CLIENT_SECRET=${GOOGLE_OAUTH_CLIENT_SECRET} \
        gmvault_arm64 "$@"
}
