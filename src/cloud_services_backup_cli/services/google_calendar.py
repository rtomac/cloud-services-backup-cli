from ..lib import register_service
from ..tools.vdirsyncer import VDirSyncerService


@register_service("google-calendar")
class GoogleCalendar(VDirSyncerService):
    """
Backs up a user's Google Calendars using vdirsyncer via CalDAV.

Each calendar is synced into its own subdirectory under the backup path,
with one .ics file per event (not one file per calendar).

Subcommands:
  setup <google_username>
        Runs an auth flow with Google to create an access token and
        runs discovery to find all calendars.
  copy <google_username>
        Syncs calendar events to a staging directory, then rsyncs to the backup
        directory without --delete, so locally-deleted events are preserved.
  sync <google_username>
        Syncs calendar events directly to the backup directory, including
        deletions for events that have been removed remotely.

OAuth2 authentication:
  vdirsyncer *requires* use ofyour own Google OAuth2 client, so
  these environment variables are required: 
  - GOOGLE_OAUTH_CLIENT_ID
  - GOOGLE_OAUTH_CLIENT_SECRET

  Your Google OAuth2 client must:
  - Have "CalDAV" API enabled on the project
  - Be configured as a "Desktop application"
  - Allow "https://www.googleapis.com/auth/calendar" scope

  For more info, see:
  https://vdirsyncer.pimutils.org/en/stable/config.html#google
    """

    storage_type = "google_calendar"
    file_ext = ".ics"

    def __init__(self, username: str):
        super().__init__(username)
