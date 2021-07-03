# Runs a `gcardvault sync`.
#
# In "copy" mode, downloads and saves all the user's
# contacts from Google Contacts.
#
# In "sync" mode, downloads/saves all contacts, and removes
# any contacts on disk that are not longer available
# in Google.
function cmd_google_contacts {
    google_username=${1:?google_username arg required}

    app_slug=google_contacts
    user_slug=${google_username//[^[:alnum:]]/_}
    user_confd=${BACKUPCONFD}/gcardvault/${user_slug}
    user_backupd=${BACKUPDATAD}/${app_slug}/${user_slug}

    flags=""
    [ ! -z "$GOOGLE_OAUTH_CLIENT_ID" ] && flags+=" --client-id ${GOOGLE_OAUTH_CLIENT_ID}"
    [ ! -z "$GOOGLE_OAUTH_CLIENT_SECRET" ] && flags+=" --client-secret ${GOOGLE_OAUTH_CLIENT_SECRET}"
    [ "${mode}" == "sync" ] && flags+=" --clean"

    echo "Using config at ${user_confd}"
    echo "Backing up to ${user_backupd}"
    _run_gcardvault sync "${google_username}" ${flags}
}
