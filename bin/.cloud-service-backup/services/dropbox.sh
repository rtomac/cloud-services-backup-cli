# Runs an `rclone copy` or `rclone sync`.
#
# In "copy" mode, copies all new and modified files from Dropbox
# to local, but does not delete files locally (protects
# against accidental or malicious deletion in Dropbox).
#
# In "sync" mode, copies all new and modified files and deletes
# all files locally which have been deleted in Dropbox.
function cmd_dropbox {
    dropbox_username=${1:?dropbox_username arg required}
    mode=${2:-copy}
    [ "${mode}" != "copy" ] && [ "${mode}" != "sync" ] && echo "Invalid mode" && exit 1

    app_slug=dropbox
    user_slug=${dropbox_username//[^[:alnum:]]/_}
    user_backupd=${BACKUPDATAD}/${app_slug}/${user_slug}
    rclone_remote=${app_slug}-${user_slug}

    if ! _check_rclone_remote "${rclone_remote}"; then
        _run_rclone config create "${rclone_remote}" dropbox config_is_local false
        echo "Created rclone remote ${rclone_remote}"
    fi

    operation=copy
    [ "${mode}" == "sync" ] && operation=sync

    echo "Using config at ${rclone_confd} with rclone remote ${rclone_remote}"
    echo "Backing up to ${user_backupd}"
    _run_rclone ${operation} --stats 0 "${rclone_remote}":/ "${user_backupd}"
}
