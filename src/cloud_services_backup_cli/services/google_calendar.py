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
  If you are providing your own Google OAuth2 client (via environment
  variables), you will need to ensure the correct APIs and OAuth2 scopes
  are enabled. See:
  https://vdirsyncer.pimutils.org/en/stable/supported.html#google
    """

    def __init__(self, username: str):
        super().__init__("google_calendar", username)
