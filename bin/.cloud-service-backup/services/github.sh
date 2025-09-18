function svc_github_help {
    cat <<EOF
Backs up GitHub repos owned by the specified user using
git and the GitHub API.

Subcommands:
  setup <github_username>
        Requests and stores a personal access token from GitHub
        to make API requests and clone repos.
  copy <github_username>
        Fetches repos and clones them as bare repositories locally.
  sync <github_username>
        Removes local repos and re-clones all repos.

Personal access tokens:
  Ensure you create personal access tokens with the following
  permissions:
   - Contents: read-only
   - Metadata: read-only
EOF
}

function svc_github_init {
    github_username=${1:?github_username arg required}

    app_slug=github
    user_slug=${github_username//[^[:alnum:]]/_}
    user_confd=${CLOUD_BACKUP_CONFD}/${app_slug}/${user_slug}
    user_backupd=${CLOUD_BACKUP_DATAD}/${app_slug}/${user_slug}

    mkdir -p "${user_confd}"
    mkdir -p "${user_backupd}"

    access_token_file=${user_confd}/.git-access-token
    credentials_file=${user_confd}/.git-credentials
    repos_file=${user_confd}/repos

    echo "Using config at ${user_confd}"
    echo "Backing up to ${user_backupd}"
}

function svc_github_setup {
    git_set_access_token "github.com" "${github_username}"
}

function svc_github_copy { svc_github_backup; }
function svc_github_sync { svc_github_backup; }
function svc_github_backup {
    git_ensure_access_token "github.com" "${github_username}"

    access_token=`cat ${access_token_file}`
    python "${tools_path}/list-github-repos.py" "${github_username}" "${access_token}" > ${repos_file}

    [ "${subcommand}" == "sync" ] && rm -r "${user_backupd}" && mkdir -p "${user_backupd}" \
        && echo "Removed existing git repos"

    git_mirror_repos ${repos_file}
}
