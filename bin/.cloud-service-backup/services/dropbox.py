from lib import *
from tools.rclone import *

@register_service("dropbox")
class Dropbox(RcloneService):
    """
Backs up Dropbox using rclone with a 'dropbox' remote.

Subcommands:
  setup <dropbox_username>
        Runs an auth flow with Dropbox to create an access token.
  copy <dropbox_username>
        Runs an 'rclone copy' that will overwrite existing files
        but will not delete files locally that have been deleted remotely.
  sync <dropbox_username>
        Runs an 'rclone sync' that will overwrite existing files
        and delete files locally that have been deleted remotely.
    """

    def __init__(self, username: str):
        super().__init__(
            "dropbox",
            require_username(username, "dropbox_username"))

    def _create_remote_silent(self) -> None:
        rclone_create_remote_silent(self.rclone_remote, "dropbox")

    def _backup(self, subcommand: str, *args: str) -> None:
        print(f"Starting rclone backup with {subcommand} command...")
        rclone(
            subcommand,
            "--stats-log-level", "NOTICE",
            "--stats", "1m",
            f"{self.rclone_remote}:/",
            f"{self.user_backupd}/",
        )
