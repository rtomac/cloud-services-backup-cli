function _cmd_bitbucket_help() {
    cat << EOF
Syncs public and private repos in Bitbucket.

To setup:

  cloud-services-backup bitbucket setup <bitbucket-username> <bitbucket-app-password>

bitbucket-username - Bitbucket username, e.g. john.doe@gmail.com
bitbucket-app-password - Bitbucket app password for authentication

To sync:

  cloud-services-backup bitbucket sync <bitbucket-username>

bitbucket-username - Bitbucket username, e.g. john.doe@gmail.com
EOF
}

function _cmd_bitbucket_init() {
    USER_CONFD=${BACKUPCONFD}/${SERVICE_SLUG}/${USERNAME_SLUG}
    echo Using config dir ${USER_CONFD}
    mkdir -p "$USER_CONFD"

    REPO_HOST=bitbucket.org
    CREDS_FILE_PATH=${USER_CONFD}/.git-credentials
}

# Creates git credentials file.
function cmd_bitbucket_setup() {
    PASSWORD=${1:?Bitbucket app password argument required}

    echo "https://${USERNAME}:${PASSWORD}@api.bitbucket.org" > "${CREDS_FILE_PATH}"
    echo "https://${USERNAME}:${PASSWORD}@${REPO_HOST}" >> "${CREDS_FILE_PATH}"
    echo Bitbucket credentials stored at ${CREDS_FILE_PATH}
}

# Queries Bitbucket API for all users repos and sync them all.
function cmd_bitbucket_sync() {
    BASE_URI=$(grep @api.bitbucket.org "${CREDS_FILE_PATH}")
    curl -s "${BASE_URI}/2.0/repositories?role=owner&pagelen=100" \
        | parse_bitbucket_repos_json \
        | sync_git_repo_lines
}

function parse_bitbucket_repos_json() {
    read -r -d '' BITB_JSON_PARSE <<EOM
import sys, json
for repo in json.load(sys.stdin)['values']:
    if repo['scm'] == 'git':
        for clone_link in repo['links']['clone']:
            if clone_link['name'] == 'https':
                print(repo['slug'], clone_link['href']);
EOM
    python3 -c "${BITB_JSON_PARSE}"
}
