from pathlib import Path
from lib import *
from tools.rsync import *
from .google_takeout import *


@register_service("google-takeout-photos")
class GoogleTakeoutPhotos(GoogleTakeoutAddonService):
    """
To do
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
