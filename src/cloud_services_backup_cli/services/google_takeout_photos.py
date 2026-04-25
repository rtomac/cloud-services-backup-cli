from pathlib import Path
import re
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
        # Google Takeout exports a ".supplemental-metadata.json" sidecar file for each
        # media file. These are awkward to handle for two reasons:
        #
        # 1) The filename is constructed by inserting ".supplemental-metadata" before
        #    the final ".json", which makes the total filename very long. Google Takeout
        #    truncates the result when it exceeds filesystem limits, starting from the
        #    middle, which can leave anything from the full suffix to just a few chars.
        #
        # 2) Google Takeout uses two different base naming patterns before truncation:
        #      photo.jpg.supplemental-metadata.json   (media extension included)
        #      photo.supplemental-metadata.json       (media extension omitted)
        #
        # We rename all sidecar files to "<media_file>.meta.json" in the destination,
        # which avoids the truncation problem entirely.
        #
        # To do the rename efficiently we hard-link the renamed files into a temp dir
        # and rsync from there, rather than building a custom transfer loop.
        SUPPL_META_SUFFIX = ".supplemental-metadata"

        def get_meta_dest_name(
            json_file: Path,
            media_names_lc: dict[str, str],  # lowercase filename → original filename
            media_stems_lc: dict[str, str],  # lowercase stem (no ext) → original filename
        ) -> str | None:
            """
            Returns the destination filename for a JSON file, or None if the file
            has no matching media file and should be skipped.

            Google Takeout names supplemental metadata files by inserting
            ".supplemental-metadata" before the final ".json". When the resulting
            filename is too long for the filesystem, Takeout truncates it from the
            middle outward. This produces several possible shapes:

            Pattern A — media extension present, suffix intact (3+ suffixes):
              photo.jpg.supplemental-metadata.json    → photo.jpg

            Pattern A — media extension present, suffix truncated (3+ suffixes):
              photo.jpg.supplemental-metad.json       → photo.jpg
              photo.jpg.s.json                        → photo.jpg

            Pattern B — media extension omitted, suffix intact (2 suffixes):
              photo.supplemental-metadata.json        → photo.jpg

            Pattern B — media extension omitted, suffix truncated (2 suffixes):
              photo.supplemental-metad.json           → photo.jpg

            Fallback — truncation ate into the media extension itself (2 suffixes):
              photo.j.json                            → photo.jpg

            When the same photo appears in the export more than once (duplicates),
            Takeout appends a number postfix to the *suffix* rather than the stem:
              photo.jpg.supplemental-metadata(1).json → photo(1).jpg
              photo.jpg.supplemental-metadata(2).json → photo(2).jpg
              photo.supplemental-metadata(1).json     → photo(1).jpg

            Regular (non-supplemental) JSON files are passed through with their
            original filename, but only if a matching media file exists.
            """
            suffixes = json_file.suffixes
            if len(suffixes) < 2:  # Not a supplemental metadata file, skip it
                return None

            # First suffix is always ".json", second suffix is the one we
            # need to check for the supplemental metadata pattern.
            second_suffix = suffixes[-2].lower()

            # Extract number postfix if exists on second suffix, e.g.:
            #   ".supplemental-metadata(1)" → second_suffix=".supplemental-metadata", number_postfix="(1)"
            number_postfix = ""
            number_postfix_match = re.search(r"\(\d+\)$", second_suffix)
            if number_postfix_match:
                second_suffix = second_suffix[:number_postfix_match.start()]
                number_postfix = number_postfix_match.group(0)

            # Strip the suffixes to expose the media file (or stem if no ext).
            # "photo.jpg.supplemental-metadata.json" → photo.jpg   (pattern A)
            # "photo.supplemental-metadata.json"     → photo        (pattern B)
            media_base = json_file.with_suffix('').with_suffix('')

            # Check if second suffix is a (possibly truncated) ".supplemental-metadata".
            # startswith in this direction means truncated forms like ".supplemental-metad" still match.
            if len(second_suffix) > 1 and SUPPL_META_SUFFIX.startswith(second_suffix):
                if len(suffixes) >= 3:
                    # Pattern A: media_base has an extension (photo.jpg).
                    # Re-attach number postfix to stem: photo(1).jpg
                    media_name = media_base.stem + number_postfix + media_base.suffix
                    media_name_match = media_names_lc.get(media_name.lower())
                else:
                    # Pattern B: media_base is stem-only (photo).
                    # Look up by stem + postfix: photo(1)
                    media_name_match = media_stems_lc.get((media_base.name + number_postfix).lower())
                return media_name_match + ".meta.json" if media_name_match else None

            # Regular JSON: pass through unchanged if a matching media file exists.
            if media_names_lc.get(json_file.with_suffix('').name.lower()):
                return json_file.name

            # Fallback: truncation ate into the media extension itself (e.g. "photo.j.json"
            # from "photo.jpg.supplemental-metadata.json"). ".j" doesn't match
            # ".supplemental-metadata" above, so we land here. Check if name-without-.json
            # is a prefix of any media filename ("photo.j" is a prefix of "photo.jpg").
            name_prefix = json_file.with_suffix('').name.lower()
            for media_name_lc, media_name_orig in media_names_lc.items():
                if media_name_lc.startswith(name_prefix):
                    return media_name_orig + ".meta.json"

            return None

        with tempfile.TemporaryDirectory(dir=backup_tmpd()) as tmp_dir_path:
            tmp_dir = Path(tmp_dir_path)

            json_files = [f for f in list_files(source_album_dir) if f.suffix.lower() == ".json"]
            media_files = [f for f in list_files(source_album_dir) if f.suffix.lower() != ".json"]
            media_names_lc = {f.name.lower(): f.name for f in media_files}  # for exact filename lookup
            media_stems_lc = {f.stem.lower(): f.name for f in media_files}  # for stem-only lookup

            for json_file in json_files:
                dest_name = get_meta_dest_name(json_file, media_names_lc, media_stems_lc)
                if dest_name is None:
                    continue
                os.link(json_file, tmp_dir.joinpath(dest_name))

            rsync(*rsync_flags, "-v", "--include", "*.json", "--exclude", "*", f"{tmp_dir}/", f"{dest_album_dir}/")

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
