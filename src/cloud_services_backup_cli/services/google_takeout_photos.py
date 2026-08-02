from __future__ import annotations

import json
from pathlib import Path
import tempfile

from ..lib import *
from ..tools.rsync import *
from ..tools.media import *
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
  copy <google_username> [<album_name> ...]
        Downloads archive files and syncs albums to the
        albums directory in the backup dir. Additive only,
        will not remove any existing files in the backup dir.
        Limited to albums specified on the command line, or
        all albums if none are specified.
  sync <google_username> [<album_name> ...]
        Downloads archive files and syncs albums to the
        albums directory in the backup dir. Will fully sync
        albums included in an export, removing any photos
        within that album that were removed in the export,
        but will not touch any albums that aren't included
        in an export. Limited to albums specified on the
        command line, or all albums if none are specified.

How this works:
- Downloads, extracts, and manages Google Takeout archives just
  as described in the 'google-takeout' service (see help).
  After that...
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
        # Build a dict keyed by album name so that if the same album appears in
        # multiple exports, the last export seen wins. Exports are iterated in
        # chronological order (their names are timestamps), so this naturally
        # selects the most recent export for each album.
        albums_dict = {}

        for export in self.google_takeout.list_exports():
            albums_root_dir = export.takeout_root_dir().joinpath("Google Photos")
            if not albums_root_dir.exists() or not albums_root_dir.is_dir(): continue

            for album_dir in list_subdirs(albums_root_dir):
                albums_dict[album_dir.name] = (export, album_dir)
                logging.debug(f"Found album '{album_dir.name}' in export '{export.name}'")

        albums_list = sorted(albums_dict.values(), key=lambda x: (x[0].name, x[1].name))
        if len(args):
            # Filter to only the albums explicitly requested on the command line
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

        rsync_flags = ["--archive"]
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

        print(f"Synchronizing files in '{source_album_dir.name}' to library folders...")
        self.__sync_to_library(subcommand, dest_album_dir)

    def __sync_media(self, rsync_flags: list[str], source_album_dir: Path, dest_album_dir: Path) -> None:
        # Include all files *with an extension* except .txt and .json
        rsync(*rsync_flags, "-v",
              "--exclude", "*.txt", "--exclude", "*.json", "--include", "*.*", "--exclude", "*",
              f"{source_album_dir}/", f"{dest_album_dir}/")

    def __sync_metadata(self, rsync_flags: list[str], source_album_dir: Path, dest_album_dir: Path) -> None:
        # Google Takeout writes a "<media>.supplemental-metadata.json" sidecar for
        # each media file, but truncates over-long names from the middle — and
        # truncates the media filename independently — so the two names on disk are
        # lossy derivations of the same original and can't always be matched to each
        # other directly. We associate them with a two-tier matcher (see
        # lib/takeout_photo_matching.py): a cheap filename pass that resolves ~99% of
        # sidecars with no file reads, then a title-based pass that reads the "title"
        # field only for the ambiguous remainder. Each sidecar is then hard-linked
        # into a temp dir as "<media_file>.meta.json" and rsynced to the destination,
        # which sidesteps the truncated names entirely downstream.
        with tempfile.TemporaryDirectory(dir=backup_tmpd()) as tmp_dir_path:
            tmp_dir = Path(tmp_dir_path)

            json_files = [f for f in list_files(source_album_dir) if f.suffix.lower() == ".json"]
            media_files = [f for f in list_files(source_album_dir) if f.suffix.lower() != ".json"]
            json_by_name = {f.name: f for f in json_files}
            media_names = [f.name for f in media_files]

            # Pass 1: match by filename only, no reads.
            resolved, deferred = plan_filename_matches(list(json_by_name.keys()), media_names)

            # Pass 2: for the ambiguous remainder, read each sidecar's "title" field
            # (the authoritative original filename) and match on that.
            if deferred:
                titles = {name: self.__read_json_title(json_by_name[name]) for name in deferred}
                claimed = set(resolved.values())
                unmatched_media = [n for n in media_names if n not in claimed]
                resolved.update(resolve_by_title(deferred, titles, unmatched_media))

            print(f"Matched {len(resolved)} of {len(json_files)} metadata file(s) "
                  f"({len(deferred)} needed a title read)")

            for json_name, media_name in resolved.items():
                os.link(json_by_name[json_name], tmp_dir.joinpath(media_name + ".meta.json"))

            rsync(*rsync_flags, "-v", "--include", "*.json", "--exclude", "*", f"{tmp_dir}/", f"{dest_album_dir}/")

    def __read_json_title(self, json_file: Path) -> str | None:
        # The sidecar's "title" is the full, untruncated original filename (with the
        # correct extension) — the reliable key for matching when the on-disk names
        # are mangled. Returns None if the file can't be read or parsed.
        try:
            with open(json_file, "r") as f:
                return json.load(f).get("title")
        except (OSError, ValueError) as e:
            logging.warning(f"Could not read title from {json_file.name}: {e}")
            return None

    def __write_album_manifest(self, dest_album_dir: Path) -> None:
        # The manifest maps each media file to its year/month, one line per file:
        #   2026/01/photo.jpg
        #   2026/03/video.mp4
        # This is used by __sync_to_library to place files into the library folder
        # tree without having to re-read timestamps on every run.
        #
        # Determining the timestamp requires reading EXIF or video metadata, which
        # is slow. To avoid doing it on every run, we load the existing manifest and
        # re-use entries for files that are already present. Only files that are new
        # since the last run need their timestamp extracted.
        manifest_file = dest_album_dir.joinpath("manifest.txt")
        manifest_new = []
        manifest_existing = {}
        manifest_updates = 0

        # Index the existing manifest by lowercase filename for fast lookup below
        if manifest_file.exists():
            manifest = self.__read_manifest_file(manifest_file)
            for year, month, file_name in manifest:
                manifest_existing[file_name.lower()] = (year, month, file_name)

        for file in list_files(dest_album_dir):
            if file.suffix.lower() == ".txt" or file.suffix.lower() == ".json": continue
            if file.name.startswith("."): continue

            # Re-use the existing entry if we already know this file's timestamp
            existing_line = manifest_existing.get(file.name.lower())
            if existing_line:
                manifest_new.append(existing_line)
                continue

            # New file — extract the creation timestamp and add it to the manifest
            dt = MediaFileInfo(file).get_create_timestamp()
            manifest_new.append((dt.strftime("%Y"), dt.strftime("%m"), file.name))
            manifest_updates += 1

        if manifest_updates > 0:
            self.__write_manifest_file(manifest_file, manifest_new)
            print(f"Wrote updated manifest with {len(manifest_new)} total line(s), {manifest_updates} updates(s)")
        else:
            print(f"Manifest already up to date with {len(manifest_new)} line(s)")

    def __read_manifest_file(self, manifest_file: Path) -> list[tuple[str, str, str]]:
        # Each line is "YYYY/MM/filename", e.g. "2026/01/photo.jpg"
        manifest = []
        with open(manifest_file, "r") as file:
            for line in file:
                (year, month, file_name) = line.strip().split("/")
                manifest.append((year, month, file_name))
        return manifest

    def __write_manifest_file(self, manifest_file: Path, manifest: list[tuple[str, str, str]]) -> None:
        with open(manifest_file, "w") as file:
            for year, month, file_name in manifest:
                file.write(f"{year}/{month}/{file_name}\n")
        return manifest


    def __sync_to_library(self, subcommand: str, album_dir: Path) -> None:
        # The library is a flat-ish folder tree organised by year/month:
        #   library/2026/01/photo.jpg
        # Files are hard-linked (not copied) from the album dir to avoid using
        # extra disk space. The manifest tells us which year/month each file belongs to.
        manifest_file = album_dir.joinpath("manifest.txt")
        for (year, month, file_name) in self.__read_manifest_file(manifest_file):
            album_file = album_dir.joinpath(file_name)
            library_file = self.user_backupd_library.joinpath(year, month, file_name)

            if self.__sync_file_to_library(subcommand, album_file, library_file):
                print(f"Linked '{year}/{month}/{file_name}'")

            # Sync any sidecar metadata files alongside the media file.
            # We check both .json (plain) and .meta.json (renamed supplemental metadata).
            for ext in [".json", ".meta.json"]:
                meta_file = album_dir.joinpath(file_name + ext)
                if meta_file.exists():
                    library_meta_file = self.user_backupd_library.joinpath(year, month, file_name + ext)
                    if self.__sync_file_to_library(subcommand, meta_file, library_meta_file):
                        print(f"Linked '{year}/{month}/{file_name + ext}'")

    def __sync_file_to_library(self, subcommand: str, album_file: Path, library_file: Path) -> bool:
        # Case 1: library file doesn't exist yet — create it as a hard link to the album file
        if not library_file.exists():
            library_file.parent.mkdir(parents=True, exist_ok=True)
            library_file.hardlink_to(album_file)
            return True

        album_stat = album_file.stat()
        library_stat = library_file.stat()

        # Case 2: already the same inode — files are already hard-linked, nothing to do
        is_hard_linked = (album_stat.st_ino == library_stat.st_ino and album_stat.st_dev == library_stat.st_dev)
        if is_hard_linked:
            return False

        # Case 3: different inodes but same size — treat as the same photo (e.g. it
        # appears in multiple albums). Replace the album copy with a hard link to the
        # library copy so both point at a single inode and we don't store it twice.
        are_same_size = (album_stat.st_size == library_stat.st_size)
        if are_same_size:
            album_file.unlink()
            album_file.hardlink_to(library_file)
            return True

        # Case 4: files differ (e.g. the export contains an updated version of the photo).
        # In sync mode, replace the library file with the newer album file.
        if subcommand == "sync" and (album_stat.st_mtime > library_stat.st_mtime):
            library_file.unlink()
            library_file.hardlink_to(album_file)
            return True

        return False
