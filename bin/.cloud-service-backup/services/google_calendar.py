from lib import *
from tools.gcalvault import *

@register_service("google-calendar")
class GoogleCalendar(Service):
    """
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
    """

    def __init__(self, username: str):
        super().__init__(
            require_username(username, "google_username", "gmail.com"))

        user_slug = slugify(self.username)
        self.user_confd = backup_confd("gcalvault", user_slug)
        self.user_backupd = backup_datad("google_calendar", user_slug)

        self.user_confd.mkdir(parents=True, exist_ok=True)
        self.user_backupd.mkdir(parents=True, exist_ok=True)

        print(f"Using config at {self.user_confd}")
        print(f"Backing up to {self.user_backupd}")

    def setup(self, *args: str) -> None:
        print(f"Starting gcalvault login sequence for {self.username}...")
        gcalvault(self.__dict__,
            "login", self.username, *google_oauth_creds_as_args())
        print(f"Created token for {self.username}")

    def _force_setup(self) -> bool:
        # gcalvault will force setup on it's own when needed
        return False

    def _backup(self, subcommand: str, *args: str) -> None:
        flags = google_oauth_creds_as_args()
        if subcommand == "sync":
            flags += ["--clean"]

        print(f"Running gcalvault sync...")
        gcalvault(self.__dict__, "sync", self.username, *flags)
