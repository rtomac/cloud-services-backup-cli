# Runs gmvault via tianon/gmvault image.
# All args passed to gmvault.
function run_gmvault {
    : "${USER_CONFD:?Environment variable USER_CONFD is expected}"
    : "${USER_BACKUPD:?Environment variable USER_BACKUPD is expected}"
    
    docker run -it --rm \
        --log-driver syslog \
        -v "${USER_CONFD}":/root/.gmvault \
        -v "${USER_BACKUPD}":/root/gmvault-db \
        tianon/gmvault "$@"
}
