from lib import *
from tools.rclone import *


@register_service("google-drive")
class GoogleDrive(RcloneService):
    """
Backs up Google Drive using rclone with a 'drive' remote.

Subcommands:
  setup <google_username>
        Runs an auth flow with Google to create an access token.
  copy <google_username>
        Runs an 'rclone copy' that will overwrite existing files
        but will not delete files locally that have been deleted remotely.
  sync <google_username>
        Runs an 'rclone sync' that will overwrite existing files
        and delete files locally that have been deleted remotely.

OAuth2 authentication:
  If you are providing your own Google OAuth2 client (via environment
  variables), you will need to ensure the correct APIs and OAuth2 scopes
  are enabled. See:
  https://rclone.org/drive/#making-your-own-client-id
    """

    def __init__(self, username: str):
        super().__init__(
            "google_drive",
            require_username(username, "google_username", "gmail.com"))

    def _create_remote_silent(self) -> None:
        rclone_create_remote_silent(
            self.rclone_remote, "drive",
            "scope", "drive.readonly",
            *google_oauth_creds_as_args(client_id_key="client_id", client_secret_key="client_secret"))

    def _backup(self, subcommand: str, *args: str) -> None:
        print(f"Starting rclone backup with {subcommand} command...")
        rclone(
            subcommand,
            "--stats-log-level", "NOTICE",
            "--stats", "1m",
            "--exclude", "/Google Photos/",
            "--exclude", "/Takeout/",
            f"{self.rclone_remote}:/",
            f"{self.user_backupd}/",
        )
