function _cmd_github_help() {
    cat << EOF
Syncs public and private repos in GitHub.

To setup:

  cloud-services-backup github setup <github-username> <github-access-token>

github-username - GitHub username, e.g. john.doe
github-access-token - GitHub personal access token for authentication

To sync:

  cloud-services-backup gmail sync <github-username>

github-username - GitHub username, e.g. john.doe
EOF
}

function _cmd_github_init() {
    USER_CONFD=${BACKUPCONFD}/${SERVICE_SLUG}/${USERNAME_SLUG}
    echo Using config dir ${USER_CONFD}
    mkdir -p "$USER_CONFD"

    REPO_HOST=github.com
    CREDS_FILE_PATH=${USER_CONFD}/.git-credentials
}

# Creates git credentials file.
function cmd_github_setup() {
    PASSWORD=${1:?Github access token argument required}

    echo "https://${USERNAME}:${PASSWORD}@api.github.com" > "${CREDS_FILE_PATH}"
    echo "https://${USERNAME}:${PASSWORD}@${REPO_HOST}" >> "${CREDS_FILE_PATH}"
    echo GitHub credentials stored at ${CREDS_FILE_PATH}
}

# Queries GitHub API for all users repos and sync them all.
function cmd_github_sync() {
    BASE_URI=$(grep @api.github.com "${CREDS_FILE_PATH}")
    curl -s -H "accept: application/vnd.github.v3+json" "${BASE_URI}/user/repos?type=owner&per_page=100" \
        | parse_github_repos_json \
        | sync_git_repo_lines
}

function parse_github_repos_json() {
    read -r -d '' GH_JSON_PARSE <<EOM
import sys, json
for repo in json.load(sys.stdin):
    print(repo['name'], repo['clone_url']);
EOM
    python3 -c "${GH_JSON_PARSE}"
}
