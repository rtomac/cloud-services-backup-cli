function svc_gmail_help {
    cat <<EOF
Backs up Gmail inbox using Got Your Back (GYB).

Subcommands:
  setup <gmail_address>
        Sets up the OAuth2 client and runs an auth flow with Google
        to create an access token. See OAuth2 authentication
        section below for more on this.
  copy <gmail_address>
        For first-time backups, will run a full gyb backup. After
        the first backup, will pull new messages and refresh
        labels (e.g. folders) on all messages received in the
        last 90 days.
  sync <gmail_address>
        Runs a full gyb backup and refreshes labels (e.g. folders)
        on all messages in the account.

OAuth2 authentication:
  GYB requires you to provide your own Google OAuth2 client.

  If you already know what you're doing and have an OAuth2 client
  to use, see below for APIs that must be enabled and provide
  your OAUth2 client & secret via environment variables
  GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET.

  If you haven't done this before, GYB has a pretty
  excellent semi-automated but interactive process to walk you through
  creating a new GCP project and OAuth2 client in GCP console. Just run
  the 'setup' subcommand and follow the prompts.

  Google APIs:
   - Gmail API: gmail.googleapis.com
   - Google Drive API: drive.googleapis.com
   - Cloud Identity-Aware Proxy API: iap.googleapis.com
   - Google Vault API: vault.googleapis.com
   - Groups Migration API: groupsmigration.googleapis.com

  OAuth2 scopes:
   - https://www.googleapis.com/auth/gmail.readonly
   - https://www.googleapis.com/auth/drive.appdata
   - https://www.googleapis.com/auth/apps.groups.migration

  Note: When the client is set up and you're authorizing it, the flow
  will have you load a URL in your browser and log in through Google.
  If you're running this on a remote server, but loading the URL in
  a browser on your local machine, you'll find you hit an error after
  authorization with a page non found. That's okay, it's sort of
  by design to work around security restrictions Google has in place.
  Just copy the 'code' query parameter from the URL you were redirected
  to and pate it back into the terminal prompt to complete the flow.
EOF
}

function svc_gmail_init {
    gmail_address=${1:?gmail_address arg required}

    user_slug=${gmail_address//[^[:alnum:]]/_}
    user_confd=${CLOUD_BACKUP_CONFD}/gyb/${user_slug}
    user_backupd=${CLOUD_BACKUP_DATAD}/gmail/${user_slug}
    secrets_file=${user_confd}/client_secrets.json
    token_file=${user_confd}/${gmail_address}.cfg
}

function svc_gmail_setup {
    # If Google OAuth2 client ID/secret in env vars,
    # remove services file and recreate
    if [ -n "${GOOGLE_OAUTH_CLIENT_ID}" ] && [ -n "${GOOGLE_OAUTH_CLIENT_SECRET}" ]; then
        cat > "${secrets_file}" <<EOF
{
    "installed": {
        "client_id": "${GOOGLE_OAUTH_CLIENT_ID}",
        "client_secret": "${GOOGLE_OAUTH_CLIENT_SECRET}",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "redirect_uris": [ "http://localhost" ]
    }
}
EOF
    fi

    # If we couldn't create the secrets file from env vars,
    # give user the option to run through GYB's interactive
    # process to create a Google OAuth2 client of their own
    if [ ! -f "${secrets_file}" ]; then
        cat <<EOF
Google OAuth2 client ID & secret were not provided in the environment
and are required to generate an auth token for use with GYB.

To use GYB, you must create a Google OAuth2 client of your own, it
doesn't provide one for general use.

You have three options:
1. Create a Google OAuth2 client (if you haven't already),
   set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET
   environment variables, and re-run this command.
2. Create a Google OAuth2 client (if you haven't already),
   download the client_secrets.json file, save it to
   '${secrets_file}',
   and re-run this command.
3. Let GYB create a Google OAuth2 client for you by proceeding
   through the interactive process to follow.

If you already know what you're doing and have an OAuth2 client
to use, see help for APIs that must be enabled and choose
option #1 or #2 above.

If you haven't done this before, choose option #3. GYB has a pretty
excellent semi-automated but interactive process to walk you through
creating a new GCP project and OAuth2 client in GCP console.

EOF

        read -p "Would you like to continue with option #3? (y/N) " confirm
        [[ "$confirm" != [yY] ]] && exit 1
        gyb_x --email "${gmail_address}" --action create-project
    fi

    # Remove user token file and run 'quota' command to initiate auth flow
    if [ -f "${token_file}" ]; then
        rm -f "${token_file}"
    fi
    gyb_x --email "${gmail_address}" --action quota

    echo "Created auth token for user ${gmail_address}"
}

function svc_gmail_copy { svc_gmail_backup; }
function svc_gmail_sync { svc_gmail_backup; }
function svc_gmail_backup {
    if [ ! -f "${token_file}" ]; then
        svc_gmail_setup
    fi

    # [ "${subcommand}" == "sync" ] && rm -r "${user_backupd}" && mkdir -p "${user_backupd}" \
    #     && echo "Deleted existing gmail backup, initiating a full resync"

    flags=""
    if [ "${subcommand}" == "copy" ] && [ -f "${user_backupd}/msg-db.sqlite" ]; then
        flags+=" --search newer_than:90d"
        #flags+=" --search newer_than:12m --fast-incremental"
    fi

    echo "Using config at ${user_confd}"
    echo "Backing up to ${user_backupd}"
    gyb_x --email "${gmail_address}" --action backup ${flags}
}
