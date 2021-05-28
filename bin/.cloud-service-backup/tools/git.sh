function _ensure_git_access_token {
    repo_host=${1:?repo_host arg required}
    git_username=${2:?git_username arg required}

    : "${user_confd:?user_confd env variable expected}"
    : "${access_token_file:?access_token_file env variable expected}"
    : "${credentials_file:?credentials_file env variable expected}"

    if [ ! -f "${access_token_file}" ] || [ ! -f "${credentials_file}" ]; then
        echo "Enter git access token:"
        read access_token

        echo -n "${access_token}" > "${access_token_file}"
        echo "https://${git_username}:${access_token}@${repo_host}" > "${credentials_file}"
        echo "git credentials saved in ${user_confd}"
    fi
}

function _mirror_git_repos {
    repos_file=${1:?repos_file arg required}

    : "${user_backupd:?user_backupd env variable expected}"
    : "${credentials_file:?credentials_file env variable expected}"

    cat "${repos_file}" | while read clone_url 
    do
        repo_name=${clone_url##*/}
        repo_dir=${user_backupd}/${repo_name}

        if [ ! -d "${repo_dir}" ]; then
            echo "Creating mirror of ${repo_name}"
            git config --global credential.helper "store --file ${credentials_file}"
            git clone --mirror --config credential.helper="store --file ${credentials_file}" "${clone_url}" "${repo_dir}"
            git config --global --unset credential.helper
        else
            echo "Updated mirror of ${repo_name}"
            git --git-dir "${repo_dir}" remote update
        fi
    done
}
