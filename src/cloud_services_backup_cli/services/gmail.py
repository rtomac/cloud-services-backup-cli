import json

from ..lib import *
from ..tools.gyb import *


@register_service("gmail")
class Gmail(Service):
    """
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
    """

    def __init__(self, username: str):
        self.username = require_username(username, "gmail_address", "gmail.com")

        user_slug = slugify(self.username)
        self.user_confd = backup_confd("gyb", user_slug)
        self.user_backupd = backup_datad("gmail", user_slug)
        self.secrets_file = self.user_confd.joinpath("client_secrets.json")
        self.token_file = self.user_confd.joinpath(f"{self.username}.cfg")
        self.msg_db_file = self.user_backupd.joinpath("msg-db.sqlite")

        self.user_confd.mkdir(parents=True, exist_ok=True)
        self.user_backupd.mkdir(parents=True, exist_ok=True)

    def info(self) -> None:
        print(f"Using config at {self.user_confd}")
        print(f"Backing up to {self.user_backupd}")

    def setup(self, *args: str) -> None:
        # If Google OAuth2 client ID/secret in env vars,
        # remove credentials file and recreate
        creds = google_oauth_creds()
        if creds:
            client_id, client_secret = creds
            secrets_cfg = {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "redirect_uris": ["http://localhost"]
                }
            }
            with open(self.secrets_file, "w") as f:
                json.dump(secrets_cfg, f, indent=4)
            print(f"Wrote OAuth2 client secrets to {self.secrets_file}")

        # If we couldn't create the secrets file from env vars,
        # give user the option to run through GYB's interactive
        # process to create a Google OAuth2 client of their own
        if not self.secrets_file.exists():
            print(self.__get_oauth_client_instr())
            confirm = input("Would you like to continue with option #3? (y/N) ")
            if confirm.lower() != "y":
                exit(1)
            gyb(self.__dict__, "--email", self.username, "--action", "create-project")

        # Remove user token file and run 'quota' command to force an auth flow
        if self.token_file.exists():
            self.token_file.unlink()
        gyb(self.__dict__, "--email", self.username, "--action", "quota")

        print(f"Created auth token for user {self.username}")

    def setup_required(self) -> bool:
        return not self.token_file.exists()

    def _backup(self, subcommand: str, *args: str) -> None:
        # if subcommand == "sync":
        #     if self.user_backupd.exists():
        #         shutil.rmtree(self.user_backupd)
        #     self.user_backupd.mkdir(parents=True, exist_ok=True)
        #     print("Deleted existing gmail backup, initiating a full resync")

        flags = []
        if subcommand == "copy" and self.msg_db_file.exists():
            flags += ["--search", "newer_than:90d"]
            #flags += ["--search", "newer_than:12m", "--fast-incremental"]

        print(f"Starting gyb backup...")
        gyb(self.__dict__, "--email", self.username, "--action", "backup", *flags)

    def __get_oauth_client_instr(self) -> str:
        return f"""
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
   '{self.secrets_file}',
   and re-run this command.
3. Let GYB create a Google OAuth2 client for you by proceeding
   through the interactive process to follow. (Must be run on
   a machine with a web browser.)

If you already know what you're doing and have an OAuth2 client
to use, see help for APIs that must be enabled and choose
option #1 or #2 above.

If you haven't done this before, choose option #3. GYB has a pretty
excellent semi-automated but interactive process to walk you through
creating a new GCP project and OAuth2 client in GCP console.
        """
