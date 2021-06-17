# Runs a `gcalvault sync`.
#
# In "copy" mode, downloads and saves all calendars visible
# to the user in Google Calendar.
#
# In "sync" mode, downloads/saves all calendars, and removes
# any calendars on disk that are not longer available
# in Google.
function cmd_google_calendar {
    google_username=${1:?google_username arg required}

    app_slug=google_calendar
    user_slug=${google_username//[^[:alnum:]]/_}
    user_confd=${BACKUPCONFD}/gcalvault/${user_slug}
    user_backupd=${BACKUPDATAD}/${app_slug}/${user_slug}

    flags=""
    [ ! -z "$GOOGLE_OAUTH_CLIENT_ID" ] && flags+=" --client-id ${GOOGLE_OAUTH_CLIENT_ID}"
    [ ! -z "$GOOGLE_OAUTH_CLIENT_SECRET" ] && flags+=" --client-secret ${GOOGLE_OAUTH_CLIENT_SECRET}"
    [ "${mode}" == "sync" ] && flags+=" --clean"

    echo "Using config at ${user_confd}"
    echo "Backing up to ${user_backupd}"
    _run_gcalvault sync "${google_username}" ${flags}
}
