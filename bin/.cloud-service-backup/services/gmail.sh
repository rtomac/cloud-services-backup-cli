# Runs a `gmvault sync`.
#
# In "quick" mode, syncs the last 10 days worth of new email
# and won't delete any deleted messages (protects against
# accidental or malicious deletion in Gmail).
#
# In "full" mode, syncs all email, and deletes all messages
# which have been deleted in Gmail.
function cmd_gmail {
    gmail_address=${1:?gmail_address arg required}
    sync_type=${2:-quick}

    user_slug=${gmail_address//[^[:alnum:]]/_}
    user_confd=${BACKUPCONFD}/gmvault/${user_slug}
    user_backupd=${BACKUPDATAD}/gmail/${user_slug}

    check_db=no
    [ "${sync_type}" = "full" ] && check_db=yes

    echo "Using config at ${user_confd}"
    echo "Backing up to ${user_backupd}"
    _run_gmvault sync --type "${sync_type}" --check-db ${check_db} "${gmail_address}"
}
