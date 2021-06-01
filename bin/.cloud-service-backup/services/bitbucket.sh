# Fetches repos owned by the specified user and clones
# them as bare repositories locally.
#
# In "sync" mode, all local repos will be removed and all
# repos within Bitbucket will be re-cloned.
function cmd_bitbucket {
    bitbucket_username=${1:?bitbucket_username arg required}

    user_slug=${bitbucket_username//[^[:alnum:]]/_}
    user_confd=${BACKUPCONFD}/bitbucket/${user_slug}
    user_backupd=${BACKUPDATAD}/bitbucket/${user_slug}

    mkdir -p "${user_confd}"
    mkdir -p "${user_backupd}"

    access_token_file=${user_confd}/.git-access-token
    credentials_file=${user_confd}/.git-credentials
    repos_file=${user_confd}/repos

    _ensure_git_access_token "bitbucket.org" "${bitbucket_username}"

    access_token=`cat ${access_token_file}`
    python3 "${tools_path}/list-bitbucket-repos.py" "${bitbucket_username}" "${access_token}" > ${repos_file}

    [ "${mode}" == "sync" ] && rm -r "${user_backupd}" && mkdir -p "${user_backupd}" \
        && echo "Removed existing git repos"

    _mirror_git_repos ${repos_file}
}
