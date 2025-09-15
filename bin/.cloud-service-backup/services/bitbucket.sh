function svc_bitbucket_help {
    cat <<EOF
Backs up Bitbucket repos owned by the specified user using
git and the Bitbucket API.

Subcommands:
  setup <atlassian_username>
        Requests and stores an API token from Atlassian
        to make API requests and clone repos.
  copy <atlassian_username>
        Fetches repos and clones them as bare repositories locally.
  sync <atlassian_username>
        Removes local repos and re-clones all repos.
EOF
}

function svc_bitbucket_init {
    bitbucket_username=${1:?bitbucket_username arg required}

    app_slug=bitbucket
    user_slug=${bitbucket_username//[^[:alnum:]]/_}
    user_confd=${CLOUD_BACKUP_CONFD}/${app_slug}/${user_slug}
    user_backupd=${CLOUD_BACKUP_DATAD}/${app_slug}/${user_slug}

    mkdir -p "${user_confd}"
    mkdir -p "${user_backupd}"

    access_token_file=${user_confd}/.git-access-token
    credentials_file=${user_confd}/.git-credentials
    repos_file=${user_confd}/repos
}

function svc_bitbucket_setup {
    git_set_access_token "bitbucket.org" "${bitbucket_username}"
}

function svc_bitbucket_copy { svc_bitbucket_backup; }
function svc_bitbucket_sync { svc_bitbucket_backup; }
function svc_bitbucket_backup {
    git_ensure_access_token "bitbucket.org" "${bitbucket_username}"

    access_token=`cat ${access_token_file}`
    python "${tools_path}/list-bitbucket-repos.py" "${bitbucket_username}" "${access_token}" > ${repos_file}

    [ "${subcommand}" == "sync" ] && rm -r "${user_backupd}" && mkdir -p "${user_backupd}" \
        && echo "Removed existing git repos"

    echo "Mirroring repos to ${user_backupd}"
    git_mirror_repos ${repos_file}
}
