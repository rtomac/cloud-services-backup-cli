from pathlib import Path
import tempfile
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
        if subcommand == "sync":
            rsync_flags += ["--delete"]

        print(f"Synchronizing media files in album '{source_album_dir.name}'...")
        self.__sync_media(rsync_flags, source_album_dir, dest_album_dir)

        print(f"Synchronizing metadata files in album '{source_album_dir.name}'...")
        self.__sync_metadata(rsync_flags, source_album_dir, dest_album_dir)

    def __sync_media(self, rsync_flags: list[str], source_album_dir: Path, dest_album_dir: Path) -> None:
        rsync(*rsync_flags, "--exclude", "*.txt", "--exclude", "*.json", f"{source_album_dir}/", f"{dest_album_dir}/")

    def __sync_metadata(self, rsync_flags: list[str], source_album_dir: Path, dest_album_dir: Path) -> None:
        # Sync json metadata files separately here, so we can handle absurdly named
        # ".supplemental-metadata.json" files with suffixes that are 1) very long and
        # 2) variably named based on the length of the media file name, which makes
        # them difficult to check for on file system. We'll rename these ".meta.json".
        # 
        # Use temp dir with hard-linked renamed files so we can ultimately 
        # just do an efficient rsync for these files as well.

        def is_suppl_meta_file(f: Path) -> bool:
            return len(f.suffixes) >= 3 and ".supplemental-metadata".startswith(f.suffixes[-2].lower())
        
        def rename_suppl_meta_file(f: Path) -> bool:
            return f.with_suffix('').with_suffix('').name + ".meta.json"

        with tempfile.TemporaryDirectory() as tmp_dir_path:
            tmp_dir = Path(tmp_dir_path)
            json_files = [f for f in list_files(source_album_dir) if f.suffix.lower() == ".json"]
            for json_file in json_files:
                dest_file_name = json_file.name
                if is_suppl_meta_file(json_file):
                    dest_file_name = rename_suppl_meta_file(json_file)
                os.link(json_file, tmp_dir.joinpath(dest_file_name))
            
            rsync(*rsync_flags, "--include", "*.json", "--exclude", "*", f"{tmp_dir}/", f"{dest_album_dir}/")
