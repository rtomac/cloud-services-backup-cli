function svc_google_calendar_help {
    cat <<EOF
Backs up a user's Google Calendars using gcalvault in *.ics format.

Subcommands:
  setup <google_username>
        Runs an auth flow with Google to create an access token.
  copy <google_username>
        Runs a 'gcalvault sync' that will update existing calendars
        but not delete calendars locally that have been deleted remotely.
  sync <google_username>
        Runs a 'gcalvault sync' with '--clean' flag that will update existing
        calendars and delete calendars locally that have been deleted remotely.

OAuth2 authentication:
  If you are providing your own Google OAuth2 client (via environment
  variables), you will need to ensure the correct APIs and OAuth2 scopes
  are enabled. See:
  https://github.com/rtomac/gcalvault/blob/main/README.md#oauth2-authentication
EOF
}

function svc_google_calendar_init {
    google_username=${1:?google_username arg required}

    user_slug=${google_username//[^[:alnum:]]/_}
    user_confd=${CLOUD_BACKUP_CONFD}/gcalvault/${user_slug}
    user_backupd=${CLOUD_BACKUP_DATAD}/google_calendar/${user_slug}

    mkdir -p "${user_confd}"
    mkdir -p "${user_backupd}"

    echo "Using config at ${user_confd}"
    echo "Backing up to ${user_backupd}"
}

function svc_google_calendar_setup {
    gcalvault_x login "${google_username}" $(_svc_google_calendar_flags)
    echo "Created token for ${google_username}"
}

function svc_google_calendar_copy { svc_google_calendar_backup; }
function svc_google_calendar_sync { svc_google_calendar_backup; }
function svc_google_calendar_backup {
    flags="$(_svc_google_calendar_flags)"
    [ "${subcommand}" == "sync" ] && flags+=" --clean"
    
    gcalvault_x sync "${google_username}" ${flags}
}

function _svc_google_calendar_flags {
    [ ! -z "$GOOGLE_OAUTH_CLIENT_ID" ] && echo -n " --client-id ${GOOGLE_OAUTH_CLIENT_ID}"
    [ ! -z "$GOOGLE_OAUTH_CLIENT_SECRET" ] && echo -n " --client-secret ${GOOGLE_OAUTH_CLIENT_SECRET}"
}
