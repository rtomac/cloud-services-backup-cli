function cmd_gmail {
    gmail_address=${1:?gmail_address arg required}
    sync_type=${2:?sync_type arg required}

    user_slug=${gmail_address//[^[:alnum:]]/_}
    user_confd=${BACKUPCONFD}/gmvault/${user_slug}
    user_backupd=${BACKUPDATAD}/gmail/${user_slug}

    echo "Using config at ${user_confd}"
    echo "Backing up to ${user_backupd}"
    _run_gmvault sync --type "$sync_type" "$gmail_address"
}
