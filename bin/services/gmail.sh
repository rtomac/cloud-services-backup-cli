function _cmd_gmail_help() {
    cat << EOF
Syncs gmail using gmvault.

To setup:

  cloud-services-backup gmail setup <gmail-address> [google-oauth-client-id] [google-oauth-client-secret]

gmail-address - Full gmail address, e.g. john.doe@gmail.com
google-oauth-client-id (optional) - Google OAuth client ID to use with gmvault
google-oauth-client-secret (optional) - Google OAuth client secret to use with gmvault

To sync:

  cloud-services-backup gmail sync <gmail-address> [full|quick]

gmail-address - Full gmail address, e.g. john.doe@gmail.com
[full|quick] - Full is full backup, quick is last 10 days (defaults to full)

To reset auth:

  cloud-services-backup gmail reset <gmail-address>

gmail-address - Full gmail address, e.g. john.doe@gmail.com
EOF
}

function _cmd_gmail_init() {
    USER_CONFD=${BACKUPCONFD}/gmvault/${USERNAME_SLUG}
    echo Using config dir ${USER_CONFD}

    CONF_FILE_NAME=gmvault_defaults.conf
    CONF_FILE_PATH="${USER_CONFD}/${CONF_FILE_NAME}"
}

# Creates gmvault_defaults.conf for gmvault, using OAuth client if provided.
# Removes OAuth token file if exists.
# Runs a quick sync to setup auth.
function cmd_gmail_setup() {
    GOOGLE_OAUTH_CLIENT_ID=${1}
    GOOGLE_OAUTH_CLIENT_SECRET=${2}

    [ ! -f "${CONF_FILE_PATH}" ] \
        && cp "${SERVICESD}/conf/${CONF_FILE_NAME}" "${USER_CONFD}/" \
        && echo Created ${CONF_FILE_NAME} file

    [ ! -z "${GOOGLE_OAUTH_CLIENT_ID}" ] \
        && sed -i -r "s/(gmvault_client_id=).*/\1${GOOGLE_OAUTH_CLIENT_ID}/" "${CONF_FILE_PATH}" \
        && echo Set OAuth client ID in config file

    [ ! -z "${GOOGLE_OAUTH_CLIENT_SECRET}" ] \
        && sed -i -r "s/(gmvault_client_secret=).*/\1${GOOGLE_OAUTH_CLIENT_SECRET}/" "${CONF_FILE_PATH}" \
        && echo Set OAuth client secret in config file

    cmd_gmail_reset
}

# Removes OAuth token file if exists, to force reauth.
# Runs a quick sync to setup auth.
function cmd_gmail_reset() {
    OAUTH_TOKEN_FILE=$BACKUPCONFD/gmvault/${USERNAME_SLUG}/${USERNAME}.oauth2
    [ -f "${OAUTH_TOKEN_FILE}" ] && rm "${OAUTH_TOKEN_FILE}" && echo OAuth token file removed for ${USERNAME}

    cmd_gmail_sync quick
}

function cmd_gmail_sync() {
    SYNC_TYPE="${1:-full}"

    [ ! -f "${CONF_FILE_PATH}" ] \
        && (echo "Must run 'setup' action before 'sync'" >&2) \
        && exit 1

    run_gmvault sync --type "${SYNC_TYPE}" --check-db no "${USERNAME}"
}
