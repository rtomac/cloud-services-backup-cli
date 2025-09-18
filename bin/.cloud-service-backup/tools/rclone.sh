RCLONE_CONFIG=${RCLONE_CONFIG:-"${CLOUD_BACKUP_CONFD}/rclone/rclone.conf"}
RCLONE_CONFD=$(dirname "${RCLONE_CONFIG}")

function rclone_x {
    mkdir -p ${RCLONE_CONFD}

    if command -v rclone >/dev/null 2>&1; then
        # echo Running via cmd: rclone "$@"
        rclone "$@"
        return
    fi

    docker_flags="--rm"
    [ -t 0 ] && docker_flags+=" -i" # stdin is a terminal
    [ -t 1 ] && docker_flags+=" -t" # stdout is a terminal

    # echo Running via docker: rclone "$@"
    docker run ${docker_flags} \
        -v /etc/localtime:/etc/localtime:ro \
        -v /etc/timezone:/etc/timezone:ro \
        -v "${RCLONE_CONFD}":"${RCLONE_CONFD}" \
        -v "${CLOUD_BACKUP_DATAD}":"${CLOUD_BACKUP_DATAD}" \
        -e RCLONE_CONFIG="${RCLONE_CONFIG}" \
        rclone/rclone "$@"
}

function rclone_has_remote {
    rclone_remote=${1:?rclone_remote arg required}
    rclone_x listremotes | grep -q "${rclone_remote}:"
}

function rclone_authorize_user {
    rclone_remote=${1:?rclone_remote arg required}

    # Start interactive OAuth2 flow
    rclone_x config reconnect "${rclone_remote}:"
    return

    # Implementation below was overkill,
    # for some reason I lost sight of the option above to
    # call reconnect without the --auto-confirm opt
    # and sent me down a path to get this to work well on
    # headless machine
    # 
    # But it was hard fought so leaving here for reference!
    if has_web_browser; then
        # Start interactive OAuth2 flow if we have a browser
        # --auto-confirm will skip the question on whether the user
        #   has a web browser available, we already know
        rclone_x config reconnect "${rclone_remote}:" --auto-confirm
    else
        # We're using an rclone feature that allows you to
        # dip and out of the config flow to config
        # specific properties - it's a little finnicky but
        # working well for now

        # Emit message to user to guide them through
        # remote authz using 'rclone authorize'
        rclone_x config update "${rclone_remote}" --continue --state="*oauth-remote" \
            | jq -r '.Option.Help'
        echo "Paste the token here:"
        read config_token
        
        # Save token back to rclone config
        error="$(rclone_x config update "${rclone_remote}" --continue --state="*oauth-authorize" --result "${config_token}" \
            | jq -r '.Error')"
        if [ ! -z "${error}" ]; then
            echo "Error: ${error}"
            exit 1
        fi
    fi
}
