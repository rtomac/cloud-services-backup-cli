# Reads stdin, expecting lines containing repo name and repo clone URI.
# Syncs each repo to $USER_BACKUPD via sync_git_repo function.
function sync_git_repo_lines() {
    while read LINE ; do
        VALS=($LINE);
        sync_git_repo "${VALS[0]}" "${VALS[1]}"
    done
}

# Syncs git repo to $USER_BACKUPD via `git clone --mirror`.
# Presumes credential file exists at $CREDS_FILE_PATH.
# Args:
# $1 - Repo name
# $2 - Repo clone URI, without credentials in URI
function sync_git_repo() {
    : "${BACKUPDATAD:?Environment variable BACKUPDATAD is expected}"
    : "${CREDS_FILE_PATH:?Environment variable CREDS_FILE_PATH is expected}"

    REPO_NAME=$1
    REPOD=${USER_BACKUPD}/${REPO_NAME}
    CLONE_URL=$2
    
    if [ ! -d "${REPOD}" ]; then
        AUTH_BASE_URI=$(grep "@${REPO_HOST}" "${CREDS_FILE_PATH}")
        AUTH_CLONE_URL=${CLONE_URL}
        AUTH_CLONE_URL=${AUTH_CLONE_URL/#https:\/\/${USERNAME}@${REPO_HOST}/${AUTH_BASE_URI}}
        AUTH_CLONE_URL=${AUTH_CLONE_URL/#https:\/\/${REPO_HOST}/${AUTH_BASE_URI}}

        echo Creating mirror of ${REPO_NAME} at ${REPOD}
        git clone --mirror "${AUTH_CLONE_URL}" "${REPOD}"
        git --git-dir "${REPOD}" remote set-url origin "${CLONE_URL}"
        git --git-dir "${REPOD}" config credential.helper "store --file ${CREDS_FILE_PATH}"
    else
        echo Updated mirror of ${REPO_NAME} at ${REPOD}
        git --git-dir "${REPOD}" remote update
    fi
}
