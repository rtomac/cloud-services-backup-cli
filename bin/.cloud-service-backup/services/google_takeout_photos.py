from pathlib import Path
from lib import *
from tools.rsync import *
from .google_takeout import *


@register_service("google-takeout-photos")
class GoogleTakeoutPhotos(GoogleTakeoutAddonService):
    """
Backs up Google Photos from Google Takeout archives
that are created and saved into Google Drive.

For more information on how this works, see:
  cloud-service-backup google-takeout --help

Subcommands:
  setup <google_username>
        Runs an auth flow with Google to create an access token.
  copy <google_username>
        Downloads archive files and syncs albums to the
        albums directory in the backup dir. Additive only,
        will not remove any existing files in the backup dir.
  sync <google_username>
        Downloads archive files and syncs albums to the
        albums directory in the backup dir. For albums
        included in the export, will sync them fully to the backup
        folder, removing any photos that were removed in the export.
        However, will not touch any albums that aren't
        included in the export.

OAuth2 authentication:
  If you are providing your own Google OAuth2 client (via environment
  variables), you will need to ensure the correct APIs and OAuth2 scopes
  are enabled. See:
  https://rclone.org/drive/#making-your-own-client-id
    """

    def __init__(self, username: str):
        super().__init__(
            "google_takeout_photos",
            require_username(username, "google_username", "gmail.com"))
        
        self.user_backupd_albums = self.user_backupd.joinpath("albums")
        self.user_backupd_library = self.user_backupd.joinpath("library")

        self.user_backupd_albums.mkdir(parents=True, exist_ok=True)
        self.user_backupd_library.mkdir(parents=True, exist_ok=True)

    def _backup_takeout_files(self, subcommand: str, *args: str) -> None:
        print("Backing up from local takeout backup...")
        self.__sync_exports(subcommand)

    def __sync_exports(self, subcommand: str) -> None:
        for extract_dir in self.google_takeout.get_extract_dirs():
            source_root_dir = extract_dir.joinpath("Takeout", "Google Photos")
            if not source_root_dir.exists() or not source_root_dir.is_dir(): continue

            print(f"Synchronizing albums from export '{extract_dir.name}'...")
            for source_album_dir in list_subdirs(source_root_dir):
                dest_album_dir = self.user_backupd_albums.joinpath(source_album_dir.name)
                self.__sync_album(subcommand, source_album_dir, dest_album_dir)

    def __sync_album(self, subcommand: str, source_album_dir: Path, dest_album_dir: Path) -> None:
        rsync_flags = ["--archive", "--update", "-v"]
        if subcommand == "sync":
            rsync_flags.append("--delete")

        print(f"Synchronizing album '{source_album_dir.name}'...")
        rsync(*rsync_flags, f"{source_album_dir}/", f"{dest_album_dir}/")
