from lib import *
from tools.rclone import *


@register_service("google-photos")
class GooglePhotos(RcloneService):
    """
Backs up Google Photos using rclone with a 'google photos' remote.

WARNING: rclone uses Google Photos API, which has significant limitations,
preventing a full backup of photos and videos. Unfortunately it's
not that useful any more. See:
https://rclone.org/googlephotos/

Subcommands:
  setup <google_username>
        Runs an auth flow with Google to create an access token.
  copy <google_username> <year>
        Runs an 'rclone copy' for photos in the specified year
        that will add new photos but will not delete photos locally
        that have been deleted remotely.
  sync <google_username> <year>
        Runs an 'rclone sync' for photos in the specified year
        that will add new photos and delete photos locally
        that have been deleted remotely.

OAuth2 authentication:
  If you are providing your own Google OAuth2 client (via environment
  variables), you will need to ensure the correct APIs and OAuth2 scopes
  are enabled. See:
  https://rclone.org/googlephotos/#making-your-own-client-id
    """

    def __init__(self, username: str):
        super().__init__(
            "google_photos",
            require_username(username, "google_username", "gmail.com"))

    def _create_remote_silent(self) -> None:
        rclone_create_remote_silent(
            self.rclone_remote, "google photos",
            "scope", "photoslibrary.readonly",
            *google_oauth_creds_as_args(client_id_key="client_id", client_secret_key="client_secret"))
        
    def _backup(self, subcommand: str, *args: str) -> None:
        year = require_arg(args, 0, "year")
        year_backupd = f"{self.user_backupd}/{year}"

        flags = []
        if subcommand == "copy":
            flags += ["--ignore-existing"]

        print(f"Starting rclone backup with {subcommand} command...")
        rclone(
            subcommand,
            "--stats-log-level", "NOTICE",
            "--stats", "1m",
            *flags,
            f"{self.rclone_remote}:/media/by-year/{year}/",
            f"{year_backupd}/",
        )
    