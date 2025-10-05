from pathlib import Path
from lib import *
from tools.rsync import *
from .google_takeout import *


METADATA_SUFFIX_IN = ".supplemental-metada.json"
METADATA_SUFFIX_OUT = ".meta.json"


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
        self.__sync_exports_to_albums(subcommand)


    def __sync_exports_to_albums(self, subcommand: str) -> None:
        for export in self.google_takeout.list_exports():
            source_root_dir = export.takeout_root_dir().joinpath("Google Photos")
            if not source_root_dir.exists() or not source_root_dir.is_dir(): continue

            print(f"Synchronizing albums from export '{export.name}'...")
            for source_album_dir in list_subdirs(source_root_dir):
                dest_album_dir = self.user_backupd_albums.joinpath(source_album_dir.name)
                self.__sync_album(subcommand, source_album_dir, dest_album_dir)

    def __sync_album(self, subcommand: str, source_album_dir: Path, dest_album_dir: Path) -> None:
        dest_album_dir.mkdir(parents=True, exist_ok=True)

        rsync_flags = ["--archive", "--update", "-v"]
        rsync_flags += ["--exclude", "*.txt", "--exclude", "*.json"]
        if subcommand == "sync":
            rsync_flags += ["--delete"]

        print(f"Synchronizing media files in album '{source_album_dir.name}'...")
        rsync(*rsync_flags, f"{source_album_dir}/", f"{dest_album_dir}/")

        print(f"Synchronizing metadata files in album '{source_album_dir.name}'...")
        self.__sync_metadata(subcommand, source_album_dir, dest_album_dir)


    def __sync_metadata(self, subcommand: str, source_album_dir: Path, dest_album_dir: Path) -> None:
        source_file_stems = [
            f.name[:-len(METADATA_SUFFIX_IN)] for f in list_files(source_album_dir)
            if f.name.lower().endswith(METADATA_SUFFIX_IN)
        ]
        for source_file_stem in source_file_stems:
            source_file = source_album_dir.joinpath(source_file_stem + METADATA_SUFFIX_IN)
            dest_file = dest_album_dir.joinpath(source_file_stem + METADATA_SUFFIX_OUT)
            rsync("--archive", "--update", "--out-format=%n", f"{source_file}", f"{dest_file}")
            break

        if subcommand == "sync":
            dest_file_stems = [
                f.name[:-len(METADATA_SUFFIX_OUT)] for f in list_files(dest_album_dir)
                if f.name.lower().endswith(METADATA_SUFFIX_OUT)
            ]
            dest_file_stems_del = [x for x in dest_file_stems if x not in source_file_stems]
            for dest_file_stem in dest_file_stems_del:
                dest_file = dest_album_dir.joinpath(dest_file_stem + METADATA_SUFFIX_OUT)
                dest_file.unlink(missing_ok=True)
                print(f"Removed {dest_file.name}")
