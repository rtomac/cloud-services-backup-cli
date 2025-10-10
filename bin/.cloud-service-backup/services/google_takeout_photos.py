from pathlib import Path
import tempfile
from lib import *
from tools.rsync import *
from tools.media import *
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

How this works:
- Uses rclone with a 'drive' remote, the same remote used for the
  'google-drive' service. Downloads archive files (only) from
  the 'Takeout' folder in Google Drive into a local 'archives' folder.
  In 'sync' mode, will also delete any local archive files that were
  removed from Google Drive.
- Detects which archive files belong to the same export and extracts
  them into "joined" export folders in the 'archives' folder.
- Will clean up any export folders that no longer have corresponding
  archive files.
- Scans all export folders for Google Photos albums and syncs them
  into the 'albums' folder in the backup dir. Will only sync the 
  latest export it can find *for each album*.
- Syncs media files and JSON metadata files. In 'copy' mode, will
  never overwrite existing files. In 'sync' mode, will overwrite
  files where the modification time is newer than the existing file
  and will delete files that were removed in the export for that
  album. Albums that aren't included in the export are not touched.
- Generates a manifest.txt file in each album folder that lists
  all media files in the album, organized by year/month.
- Year/month is determined by the creation date of the media file.
  Several strategies are used to determine the create date, including
  EXIF metadata, video container metadata, JSON metadata, file
  name patterns, and finally falling back to shelling out to
  exiftool.
- Then, syncs media files and JSON metadata files from the album
  to the 'library' folder by date and month, as specified in the
  manifest file, using hard links to avoid using additional
  disk space. The library folder is ultimately meant to be the
  permanent archive/backup of all photos.
- In 'copy' mode, will never overwrite existing hard links. In
  'sync' mode, will overwrite hard links where the modification
  time is newer than the existing hard link and/or the file size
  is different.

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
        self.__sync_exports_to_albums(subcommand, *args)


    def __list_albums_to_sync(self, *args: str) -> list[(GoogleTakeoutExport, Path)]:
        albums_dict = {}

        for export in self.google_takeout.list_exports():
            albums_root_dir = export.takeout_root_dir().joinpath("Google Photos")
            if not albums_root_dir.exists() or not albums_root_dir.is_dir(): continue

            for album_dir in list_subdirs(albums_root_dir):
                albums_dict[album_dir.name] = (export, album_dir)
                logging.debug(f"Found album '{album_dir.name}' in export '{export.name}'")

        albums_list = sorted(albums_dict.values(), key=lambda x: (x[0].name, x[1].name))
        if len(args):
            args_lower = set(a.lower().strip() for a in args)
            albums_list = [a for a in albums_list if a[1].name.lower().strip() in args_lower]
        [logging.debug(f"Will sync album '{source_album_dir.name}' from export '{export.name}'")
            for (export, source_album_dir) in albums_list]

        return albums_list


    def __sync_exports_to_albums(self, subcommand: str, *args: str) -> None:
        for album in self.__list_albums_to_sync(*args):
            (export, source_album_dir) = album
            print(f"Synchronizing album '{source_album_dir.name}' in export '{export.name}'")
            dest_album_dir = self.user_backupd_albums.joinpath(source_album_dir.name)
            self.__sync_album(subcommand, source_album_dir, dest_album_dir)

    def __sync_album(self, subcommand: str, source_album_dir: Path, dest_album_dir: Path) -> None:
        dest_album_dir.mkdir(parents=True, exist_ok=True)

        rsync_flags = ["--archive", "-v"]
        if subcommand == "copy":
            rsync_flags += ["--ignore-existing"]
        elif subcommand == "sync":
            rsync_flags += ["--update", "--delete"]

        print(f"Synchronizing media files in album '{source_album_dir.name}'...")
        self.__sync_media(rsync_flags, source_album_dir, dest_album_dir)

        print(f"Synchronizing metadata files in album '{source_album_dir.name}'...")
        self.__sync_metadata(rsync_flags, source_album_dir, dest_album_dir)

        print(f"Writing manifest for album '{source_album_dir.name}'...")
        self.__write_album_manifest(dest_album_dir)

        print(f"Synchronizing photos in '{source_album_dir.name}' to library folders...")
        self.__sync_to_library(subcommand, dest_album_dir)

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

    def __write_album_manifest(self, dest_album_dir: Path) -> None:
        manifest_file = dest_album_dir.joinpath("manifest.txt")
        manifest_lines = []
        manifest_existing = {}
        manifest_updates = 0

        # Read existing manifest
        if manifest_file.exists():
            manifest = self.__read_manifest_file(manifest_file)
            for year, month, file_name in manifest:
                manifest_existing[file_name.lower()] = f"{year}/{month}/{file_name}"

        # Add new files
        for file in list_files(dest_album_dir):
            if file.suffix.lower() == ".txt" or file.suffix.lower() == ".json": continue
            if file.name.startswith("."): continue

            existing_line = manifest_existing.get(file.name.lower())
            if existing_line:
                manifest_lines.append(existing_line)
                continue

            dt = MediaFileInfo(file).get_create_timestamp()
            year_mo = dt.strftime("%Y/%m")
            manifest_lines.append(f"{year_mo}/{file.name}")
            manifest_updates += 1

        # Write updated manifest file
        if manifest_updates > 0:
            with open(manifest_file, "w") as file:
                for line in manifest_lines:
                    file.write(line + "\n")
            print(f"Wrote updated manifest with {len(manifest_lines)} total line(s), {manifest_updates} updates(s)")
        else:
            print(f"Manifest already up to date with {len(manifest_lines)} line(s)")

    def __read_manifest_file(self, manifest_file: Path) -> tuple[str, str, str]:
        manifest = []
        with open(manifest_file, "r") as file:
            for line in file:
                (year, month, file_name) = line.strip().split("/")
                manifest.append((year, month, file_name))
        return manifest


    def __sync_to_library(self, subcommand: str, album_dir: Path) -> None:
        manifest_file = album_dir.joinpath("manifest.txt")
        for (year, month, file_name) in self.__read_manifest_file(manifest_file):
            album_file = album_dir.joinpath(file_name)
            library_file = self.user_backupd_library.joinpath(year, month, file_name)
            
            if self.__sync_file_to_library(subcommand, album_file, library_file):
                print(f"Linked '{year}/{month}/{file_name}'")
            
            for ext in [".json", ".meta.json"]:
                meta_file = album_dir.joinpath(file_name + ext)
                if meta_file.exists():
                    library_meta_file = self.user_backupd_library.joinpath(year, month, file_name + ext)
                    if self.__sync_file_to_library(subcommand, meta_file, library_meta_file):
                        print(f"Linked '{year}/{month}/{file_name + ext}'")

    def __sync_file_to_library(self, subcommand: str, album_file: Path, library_file: Path) -> bool:
        if not library_file.exists():
            library_file.parent.mkdir(parents=True, exist_ok=True)
            library_file.hardlink_to(album_file)
            return True
        elif subcommand == "sync":
            album_stat = album_file.stat()
            library_stat = library_file.stat()
            if album_stat.st_size != library_stat.st_size or album_stat.st_mtime > library_stat.st_mtime:
                library_file.unlink()
                library_file.hardlink_to(album_file)
                return True
        return False
