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
  vdirsyncer *requires* use ofyour own Google OAuth2 client, so
  these environment variables are required: 
  - GOOGLE_OAUTH_CLIENT_ID
  - GOOGLE_OAUTH_CLIENT_SECRET

  Your Google OAuth2 client must:
  - Have "CardDAV" API enabled on the project
  - Be configured as a "Desktop application"
  - Allow "https://www.googleapis.com/auth/carddav" scope

  For more info, see:
  https://vdirsyncer.pimutils.org/en/stable/config.html#google
    """

    storage_type = "google_contacts"
    file_ext = ".vcf"

    def __init__(self, username: str):
        super().__init__(username)
