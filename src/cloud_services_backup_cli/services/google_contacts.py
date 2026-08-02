from ..lib import register_service
from ..tools.vdirsyncer import VDirSyncerService


@register_service("google-contacts")
class GoogleContacts(VDirSyncerService):
    """
Backs up a user's Google Contacts using vdirsyncer via CardDAV.

Contacts are synced into a subdirectory under the backup path,
with one .vcf file per contact.

Subcommands:
  setup <google_username>
        Runs an auth flow with Google to create an access token.
  copy <google_username>
        Syncs contacts to a staging directory, then rsyncs to the backup
        directory without --delete, so locally-deleted contacts are preserved.
  sync <google_username>
        Syncs contacts directly to the backup directory, including deletions
        for contacts that have been removed remotely.

OAuth2 authentication:
  If you are providing your own Google OAuth2 client (via environment
  variables), you will need to ensure the correct APIs and OAuth2 scopes
  are enabled. See:
  https://vdirsyncer.pimutils.org/en/stable/supported.html#google
    """

    def __init__(self, username: str):
        super().__init__("google_contacts", username)
