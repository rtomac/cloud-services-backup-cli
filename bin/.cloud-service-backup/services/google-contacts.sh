function svc_google_contacts_help {
    cat <<EOF
Backs up a user's Google Contacts using gcardvault in *.vcf format.

Subcommands:
  setup <google_username>
        Runs an auth flow with Google to create an access token.
  copy <google_username>
        Runs a 'gcardvault sync' that will update existing contacts
        but not delete contacts locally that have been deleted remotely.
  sync <google_username>
        Runs a 'gcardvault sync' with '--clean' flag that will update existing
        contacts and delete contacts locally that have been deleted remotely.

OAuth2 authentication:
  If you are providing your own Google OAuth2 client (via environment
  variables), you will need to ensure the correct APIs and OAuth2 scopes
  are enabled. See:
  https://github.com/rtomac/gcardvault/blob/main/README.md#oauth2-authentication
EOF
}

function svc_google_contacts_init {
    google_username=${1:?google_username arg required}

    user_slug=${google_username//[^[:alnum:]]/_}
    user_confd=${CLOUD_BACKUP_CONFD}/gcardvault/${user_slug}
    user_backupd=${CLOUD_BACKUP_DATAD}/google_contacts/${user_slug}

    mkdir -p "${user_confd}"
    mkdir -p "${user_backupd}"

    echo "Using config at ${user_confd}"
    echo "Backing up to ${user_backupd}"
}

function svc_google_contacts_setup {
    gcardvault_x login "${google_username}"
    echo "Created token for ${google_username}"
}

function svc_google_contacts_copy { svc_google_contacts_backup; }
function svc_google_contacts_sync { svc_google_contacts_backup; }
function svc_google_contacts_backup {
    flags=""
    [ ! -z "$GOOGLE_OAUTH_CLIENT_ID" ] && flags+=" --client-id ${GOOGLE_OAUTH_CLIENT_ID}"
    [ ! -z "$GOOGLE_OAUTH_CLIENT_SECRET" ] && flags+=" --client-secret ${GOOGLE_OAUTH_CLIENT_SECRET}"
    [ "${subcommand}" == "sync" ] && flags+=" --clean"
    
    gcardvault_x sync "${google_username}" ${flags}
}
